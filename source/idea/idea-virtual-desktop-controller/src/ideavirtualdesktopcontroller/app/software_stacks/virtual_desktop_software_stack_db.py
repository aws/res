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

import ideavirtualdesktopcontroller
from ideadatamodel import (
    exceptions,
    VirtualDesktopBaseOS,
    VirtualDesktopArchitecture,
    VirtualDesktopAffinity,
    VirtualDesktopTenancy,
    VirtualDesktopPlacement,
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
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()

        VirtualDesktopNotifiableDB.__init__(self, context=self.context, table_name=self.table_name, logger=self._logger)

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

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
            placement=VirtualDesktopPlacement(
                affinity=VirtualDesktopAffinity(db_entry[software_stacks_constants.SOFTWARE_STACK_DB_AFFINITY_KEY]) if db_entry.get(software_stacks_constants.SOFTWARE_STACK_DB_AFFINITY_KEY) else None,
                tenancy=VirtualDesktopTenancy(db_entry.get(software_stacks_constants.SOFTWARE_STACK_DB_TENANCY_KEY, VirtualDesktopTenancy.DEFAULT)),
                host_id=db_entry.get(software_stacks_constants.SOFTWARE_STACK_DB_HOST_ID_KEY),
                host_resource_group_arn=db_entry.get(software_stacks_constants.SOFTWARE_STACK_DB_HOST_RESOURCE_GROUP_ARN_KEY),
            ),
            projects=[],
            allowed_instance_types=Utils.get_value_as_list(software_stacks_constants.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY, db_entry, []),
            version=Utils.get_value_as_int(software_stacks_constants.SOFTWARE_STACK_DB_VERSION_KEY, db_entry, 1)
        )

        # Projects can be either enriched dicts (when get_project_details=True) or raw string IDs from DynamoDB
        for project_entry in Utils.get_value_as_list(software_stacks_constants.SOFTWARE_STACK_DB_PROJECTS_KEY, db_entry, []):
            if isinstance(project_entry, dict):
                software_stack.projects.append(Project(
                    project_id=Utils.get_value_as_string('project_id', project_entry),
                    name=Utils.get_value_as_string('name', project_entry),
                    title=Utils.get_value_as_string('title', project_entry),
                    description=Utils.get_value_as_string('description', project_entry),
                ))
            else:
                software_stack.projects.append(Project(project_id=project_entry))

        return software_stack

    @staticmethod
    def convert_software_stack_object_to_db_dict(software_stack: VirtualDesktopSoftwareStack) -> Dict:
        if Utils.is_empty(software_stack):
            return {}

        db_dict = {
            software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: software_stack.base_os.value,
            software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: software_stack.stack_id,
            software_stacks_constants.SOFTWARE_STACK_DB_NAME_KEY: software_stack.name,
            software_stacks_constants.SOFTWARE_STACK_DB_DESCRIPTION_KEY: software_stack.description,
            software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY: Utils.to_milliseconds(software_stack.created_on),
            software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY: Utils.to_milliseconds(software_stack.updated_on),
            software_stacks_constants.SOFTWARE_STACK_DB_AMI_ID_KEY: software_stack.ami_id,
            software_stacks_constants.SOFTWARE_STACK_DB_ENABLED_KEY: software_stack.enabled,
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: str(software_stack.min_storage.value),
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: software_stack.min_storage.unit.value,
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: str(software_stack.min_ram.value),
            software_stacks_constants.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: software_stack.min_ram.unit.value,
            software_stacks_constants.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: software_stack.architecture.value,
            software_stacks_constants.SOFTWARE_STACK_DB_GPU_KEY: software_stack.gpu.value,
            software_stacks_constants.SOFTWARE_STACK_DB_AFFINITY_KEY: software_stack.placement.affinity.value if software_stack.placement and software_stack.placement.affinity else None,
            software_stacks_constants.SOFTWARE_STACK_DB_TENANCY_KEY: software_stack.placement.tenancy.value if software_stack.placement and software_stack.placement.tenancy else VirtualDesktopTenancy.DEFAULT.value,
            software_stacks_constants.SOFTWARE_STACK_DB_HOST_ID_KEY: software_stack.placement.host_id if software_stack.placement else None,
            software_stacks_constants.SOFTWARE_STACK_DB_HOST_RESOURCE_GROUP_ARN_KEY: software_stack.placement.host_resource_group_arn if software_stack.placement else None,
            software_stacks_constants.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY: software_stack.allowed_instance_types,
            software_stacks_constants.SOFTWARE_STACK_DB_VERSION_KEY: software_stack.version
        }

        project_ids = []
        if software_stack.projects:
            for project in software_stack.projects:
                project_ids.append(project.project_id)

        db_dict[software_stacks_constants.SOFTWARE_STACK_DB_PROJECTS_KEY] = project_ids
        return db_dict

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

    def update(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        db_entry = self.convert_software_stack_object_to_db_dict(software_stack)
        db_entry[software_stacks_constants.SOFTWARE_STACK_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY, software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY, software_stacks_constants.SOFTWARE_STACK_DB_CREATED_ON_KEY, software_stacks_constants.SOFTWARE_STACK_DB_VERSION_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        update_expression = "SET " + ", ".join(update_expression_tokens) + " ADD #version :version"
        expression_attr_values[":version"] = 1
        expression_attr_names["#version"] = "version"

        result = self._table.update_item(
            Key={
                software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: db_entry[software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY],
                software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY: db_entry[software_stacks_constants.SOFTWARE_STACK_DB_RANGE_KEY]
            },
            UpdateExpression=update_expression,
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
                software_stacks_constants.SOFTWARE_STACK_DB_HASH_KEY: software_stack.base_os.value,
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
