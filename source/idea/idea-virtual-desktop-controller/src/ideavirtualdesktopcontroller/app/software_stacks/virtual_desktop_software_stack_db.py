#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
from typing import Optional, Dict

import yaml

import ideavirtualdesktopcontroller
from ideadatamodel import (
    exceptions,
    VirtualDesktopBaseOS,
    VirtualDesktopArchitecture,
    VirtualDesktopSoftwareStack,
    SocaMemory,
    SocaMemoryUnit,
    Project,
    GetProjectRequest,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    SocaListingPayload,
    SocaPaginator
)
from ideadatamodel.virtual_desktop.virtual_desktop_model import VirtualDesktopGPU
from ideasdk.utils import Utils, scan_db_records
from ideavirtualdesktopcontroller.app.virtual_desktop_notifiable_db import VirtualDesktopNotifiableDB
from ideavirtualdesktopcontroller.app.software_stacks import constants as software_stacks_constants


class VirtualDesktopSoftwareStackDB(VirtualDesktopNotifiableDB):
    DEFAULT_PAGE_SIZE = 10

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-software-stack-db')
        self.BASE_STACKS_CONFIG_FILE = f'{self.context.get_resources_dir()}/base-software-stack-config.yaml'
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()

        VirtualDesktopNotifiableDB.__init__(self, context=self.context, table_name=self.table_name, logger=self._logger)

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY,
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY,
                            'AttributeType': 'S'
                        }
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY,
                            'KeyType': 'RANGE'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )
            self._create_base_software_stacks()

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    def _create_base_software_stacks(self):
        with open(self.BASE_STACKS_CONFIG_FILE, 'r') as f:
            base_stacks_config = yaml.safe_load(f)

        if Utils.is_empty(base_stacks_config):
            self._logger.error(f'{self.BASE_STACKS_CONFIG_FILE} file is empty. Returning')
            return

        for base_os in VirtualDesktopBaseOS:
            software_stacks_seen = set()
            self._logger.info(f'Processing base_os: {base_os}')
            os_config = base_stacks_config.get(base_os)
            for arch in VirtualDesktopArchitecture:
                arch_key = arch.replace('_', '-').lower()
                self._logger.info(f'Processing architecture: {arch_key} within base_os: {base_os}')
                arch_config = os_config.get(arch_key)
                if Utils.is_empty(arch_config):
                    self._logger.error(f'Entry for architecture: {arch_key} within base_os: {base_os}. '
                                       f'NOT FOUND. Returning')
                    continue

                default_name = arch_config.get('default-name')
                default_description = arch_config.get('default-description')
                default_min_storage_value = arch_config.get('default-min-storage-value')
                default_min_storage_unit = arch_config.get('default-min-storage-unit')
                default_min_ram_value = arch_config.get('default-min-ram-value')
                default_min_ram_unit = arch_config.get('default-min-ram-unit')
                if Utils.is_empty(default_name) or Utils.is_empty(default_description) or Utils.is_empty(default_min_storage_value) or Utils.is_empty(default_min_storage_unit) or Utils.is_empty(default_min_ram_value) or Utils.is_empty(default_min_ram_unit):
                    error_message = f'Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch Config: ' \
                                    f'{arch}. Missing default-name and/or default-description and/or default-min-storage-value ' \
                                    f'and/or default-min-storage-unit and/or default-min-ram-value and/or default-min-ram-unit'
                    self._logger.error(error_message)
                    raise exceptions.invalid_params(error_message)

                aws_region = self.context.config().get_string('cluster.aws.region', required=True)
                self._logger.info(f'Processing arch: {arch_key} within base_os: {base_os} '
                                  f'for aws_region: {aws_region}')

                region_configs = arch_config.get(aws_region)
                if Utils.is_empty(region_configs):
                    self._logger.error(f'Entry for arch: {arch_key} within base_os: {base_os}. '
                                       f'for aws_region: {aws_region} '
                                       f'NOT FOUND. Returning')
                    continue

                for region_config in region_configs:
                    ami_id = region_config.get('ami-id')
                    if Utils.is_empty(ami_id):
                        error_message = f'Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch' \
                                        f' Config: {arch} AWS-Region: {aws_region}.' \
                                        f' Missing ami-id'
                        self._logger.error(error_message)
                        raise exceptions.general_exception(error_message)

                    ss_id_suffix = region_config.get('ss-id-suffix')
                    if Utils.is_empty(ss_id_suffix):
                        error_message = f'Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch' \
                                        f' Config: {arch} AWS-Region: {aws_region}.' \
                                        f' Missing ss-id-suffix'
                        self._logger.error(error_message)
                        raise exceptions.general_exception(error_message)

                    gpu_manufacturer = region_config.get('gpu-manufacturer')
                    if Utils.is_not_empty(gpu_manufacturer) and gpu_manufacturer not in {'AMD', 'NVIDIA', 'NO_GPU'}:
                        error_message = f'Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch' \
                                        f' Config: {arch} AWS-Region: {aws_region}.' \
                                        f' Invalid gpu-manufacturer {gpu_manufacturer} can be one of AMD, NVIDIA, NO_GPU only'

                        self._logger.error(error_message)
                        raise exceptions.general_exception(error_message)
                    elif Utils.is_empty(gpu_manufacturer):
                        gpu_manufacturer = 'NO_GPU'

                    custom_stack_name = region_config.get('name') \
                        if Utils.is_not_empty(region_config.get('name')) else default_name
                    custom_stack_description = region_config.get('description') \
                        if Utils.is_not_empty(region_config.get('description')) else default_description
                    custom_stack_min_storage_value = region_config.get('min-storage-value') \
                        if Utils.is_not_empty(region_config.get('min-storage-value')) else default_min_storage_value
                    custom_stack_min_storage_unit = region_config.get('min-storage-unit') \
                        if Utils.is_not_empty(region_config.get('min-storage-unit')) else default_min_storage_unit
                    custom_stack_min_ram_value = region_config.get('min-ram-value') \
                        if Utils.is_not_empty(region_config.get('min-ram-value')) else default_min_ram_value
                    custom_stack_min_ram_unit = region_config.get('min-ram-unit') \
                        if Utils.is_not_empty(region_config.get('min-ram-unit')) else default_min_ram_unit
                    custom_stack_gpu_manufacturer = VirtualDesktopGPU(gpu_manufacturer)

                    software_stack_id = f'{software_stacks_constants.BASE_STACK_PREFIX}-{base_os}-{arch_key}-{ss_id_suffix}'
                    software_stacks_seen.add(software_stack_id)
                    software_stack_db_entry = self.get(stack_id=software_stack_id, base_os=base_os)
                    if Utils.is_empty(software_stack_db_entry):
                        # base SS doesn't exist. creating
                        self._logger.info(f'software_stack_id: {software_stack_id}, does\'nt exist. CREATING.')
                        self.create(VirtualDesktopSoftwareStack(
                            base_os=VirtualDesktopBaseOS(base_os),
                            stack_id=software_stack_id,
                            name=custom_stack_name,
                            description=custom_stack_description,
                            ami_id=ami_id,
                            enabled=True,
                            min_storage=SocaMemory(
                                value=custom_stack_min_storage_value,
                                unit=SocaMemoryUnit(custom_stack_min_storage_unit)
                            ),
                            min_ram=SocaMemory(
                                value=custom_stack_min_ram_value,
                                unit=SocaMemoryUnit(custom_stack_min_ram_unit)
                            ),
                            architecture=VirtualDesktopArchitecture(arch),
                            gpu=custom_stack_gpu_manufacturer
                        ))

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.software-stacks'

    @staticmethod
    def convert_db_dict_to_software_stack_object(db_entry: dict) -> Optional[VirtualDesktopSoftwareStack]:
        if Utils.is_empty(db_entry):
            return None

        software_stack = VirtualDesktopSoftwareStack(
            base_os=VirtualDesktopBaseOS(Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY, db_entry)),
            stack_id=Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY, db_entry),
            name=Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_NAME_KEY, db_entry),
            description=Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_DESCRIPTION_KEY, db_entry),
            created_on=Utils.to_datetime(Utils.get_value_as_int(software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY, db_entry)),
            updated_on=Utils.to_datetime(Utils.get_value_as_int(software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY, db_entry)),
            ami_id=Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_AMI_ID_KEY, db_entry),
            enabled=Utils.get_value_as_bool(software_stacks_constants.SOFTWARE_STACK_DB_ENABLED_KEY, db_entry),
            min_storage=SocaMemory(
                value=Utils.get_value_as_float(software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY, db_entry),
                unit=SocaMemoryUnit(Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY, db_entry))
            ),
            min_ram=SocaMemory(
                value=Utils.get_value_as_float(software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY, db_entry),
                unit=SocaMemoryUnit(Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY, db_entry))
            ),
            architecture=VirtualDesktopArchitecture(Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_ARCHITECTURE_KEY, db_entry)),
            gpu=VirtualDesktopGPU(Utils.get_value_as_string(software_stacks_constants.SOFTWARE_STACK_DB_GPU_KEY, db_entry)),
            projects=[]
        )

        for project_id in Utils.get_value_as_list(software_stacks_constants.SOFTWARE_STACK_DB_PROJECTS_KEY, db_entry, []):
            software_stack.projects.append(Project(project_id=project_id))

        return software_stack

    @staticmethod
    def convert_software_stack_object_to_db_dict(software_stack: VirtualDesktopSoftwareStack) -> Dict:
        if Utils.is_empty(software_stack):
            return {}

        db_dict = {
            software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: software_stack.base_os,
            software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: software_stack.stack_id,
            software_stacks_constants.SOFTWARE_STACK_DB_NAME_KEY: software_stack.name,
            software_stacks_constants.SOFTWARE_STACK_DB_DESCRIPTION_KEY: software_stack.description,
            software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY: Utils.to_milliseconds(software_stack.created_on),
            software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY: Utils.to_milliseconds(software_stack.updated_on),
            software_stacks_constants.SOFTWARE_STACK_DB_AMI_ID_KEY: software_stack.ami_id,
            software_stacks_constants.SOFTWARE_STACK_DB_ENABLED_KEY: software_stack.enabled,
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: str(software_stack.min_storage.value),
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: software_stack.min_storage.unit,
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: str(software_stack.min_ram.value),
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: software_stack.min_ram.unit,
            software_stacks_constants.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: software_stack.architecture,
            software_stacks_constants.SOFTWARE_STACK_DB_GPU_KEY: software_stack.gpu
        }

        project_ids = []
        if software_stack.projects:
            for project in software_stack.projects:
                project_ids.append(project.project_id)

        db_dict[software_stacks_constants.SOFTWARE_STACK_DB_PROJECTS_KEY] = project_ids
        return db_dict

    def create(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        db_entry = self.convert_software_stack_object_to_db_dict(software_stack)
        db_entry[software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY] = Utils.current_time_ms()
        db_entry[software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        self._table.put_item(
            Item=db_entry
        )
        self.trigger_create_event(db_entry[software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY], db_entry[software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY], new_entry=db_entry)
        return self.convert_db_dict_to_software_stack_object(db_entry)

    def get_with_project_info(self, stack_id: str, base_os: str) -> Optional[VirtualDesktopSoftwareStack]:
        software_stack_db_entry = None
        if Utils.is_empty(stack_id) or Utils.is_empty(base_os):
            self._logger.error(f'invalid values for stack_id: {stack_id} and/or base_os: {base_os}')
        else:
            try:
                result = self._table.get_item(
                    Key={
                        software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: base_os,
                        software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: stack_id
                    }
                )
                software_stack_db_entry = result.get('Item')
            except self._ddb_client.exceptions.ResourceNotFoundException as _:
                # in this case we simply need to return None since the resource was not found
                return None
            except Exception as e:
                self._logger.exception(e)
                raise e

        software_stack_entry = self.convert_db_dict_to_software_stack_object(software_stack_db_entry)

        def _get_project(project_id):
            project = self.context.projects_client.get_project(GetProjectRequest(project_id=project_id)).project
            return {
                software_stacks_constants.SOFTWARE_STACK_DB_PROJECT_ID_KEY: project_id,
                software_stacks_constants.SOFTWARE_STACK_DB_PROJECT_NAME_KEY: project.name,
                software_stacks_constants.SOFTWARE_STACK_DB_PROJECT_TITLE_KEY: project.title
            }

        software_stack_projects = [_get_project(project_entry.project_id) for project_entry in software_stack_entry.projects]
        software_stack_entry.projects = software_stack_projects
        return software_stack_entry

    def get(self, stack_id: str, base_os: str) -> Optional[VirtualDesktopSoftwareStack]:
        software_stack_db_entry = None
        if Utils.is_empty(stack_id) or Utils.is_empty(base_os):
            self._logger.error(f'invalid values for stack_id: {stack_id} and/or base_os: {base_os}')
        else:
            try:
                result = self._table.get_item(
                    Key={
                        software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: base_os,
                        software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: stack_id
                    }
                )
                software_stack_db_entry = result.get('Item')
            except self._ddb_client.exceptions.ResourceNotFoundException as _:
                # in this case we simply need to return None since the resource was not found
                return None
            except Exception as e:
                self._logger.exception(e)
                raise e

        return self.convert_db_dict_to_software_stack_object(software_stack_db_entry)

    def update(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        db_entry = self.convert_software_stack_object_to_db_dict(software_stack)
        db_entry[software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY, software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY, software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: db_entry[software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY],
                software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: db_entry[software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY]
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_OLD'
        )

        old_db_entry = result['Attributes']
        self.trigger_update_event(db_entry[software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY], db_entry[software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY], old_entry=old_db_entry, new_entry=db_entry)
        return self.convert_db_dict_to_software_stack_object(db_entry)

    def delete(self, software_stack: VirtualDesktopSoftwareStack):
        if Utils.is_empty(software_stack.stack_id) or Utils.is_empty(software_stack.base_os):
            raise exceptions.invalid_params('stack_id and base_os are required')

        result = self._table.delete_item(
            Key={
                software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: software_stack.base_os,
                software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: software_stack.stack_id
            },
            ReturnValues='ALL_OLD'
        )
        old_db_entry = result['Attributes']
        self.trigger_delete_event(old_db_entry[software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY], old_db_entry[software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY], deleted_entry=old_db_entry)

    def list_all_from_db(self, request: ListSoftwareStackRequest) -> ListSoftwareStackResponse:
        list_result = scan_db_records(request, self._table)

        session_entries = list_result.get('Items', [])
        result = [self.convert_db_dict_to_software_stack_object(session) for session in session_entries]

        exclusive_start_key = list_result.get("LastEvaluatedKey")
        response_cursor = Utils.base64_encode(Utils.to_json(exclusive_start_key)) if exclusive_start_key else None

        return SocaListingPayload(
            listing=result,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
