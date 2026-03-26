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

import base64
import os
import logging
import random
from threading import RLock
from typing import Any, List, Dict, Optional

from ideasdk.metrics import CloudWatchAgentLogFileOptions
import ideavirtualdesktopcontroller
from botocore.exceptions import ClientError

from ideadatamodel import constants, VirtualDesktopArchitecture, Project
from ideadatamodel import (
    VirtualDesktopSession,
    VirtualDesktopBaseOS,
    BaseOS,
    VirtualDesktopGPU,
    VirtualDesktopTenancy,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopSoftwareStack,
)
from ideadatamodel.shared_filesystem import ListOnboardedFileSystemsRequest
from ideasdk.bootstrap import BootstrapUserDataBuilder
from ideasdk.context import BootstrapContext
from ideasdk.launch_configurations import ScriptOSType, ScriptEventType
from ideasdk.utils import Utils, GroupNameHelper
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils

from res.resources import cluster_settings
import res.constants as res_constants
import boto3
import json
import requests
import jwt
import time

from res.utils import table_utils, logging_utils

logger = logging_utils.get_logger(constants.MODULE_ID_VIRTUAL_DESKTOP_APP)
class VirtualDesktopControllerUtils:

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-controller-utils')
        self.s3_client = self.context.aws().s3()
        self.ec2_client = self.context.aws().ec2()
        self.eventbridge_client = self.context.aws().eventbridge()
        self.ssm_client = self.context.aws().ssm()
        self.sqs_client = self.context.aws().sqs()
        self.events_utils = EventsUtils(context=self.context)
        self.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY = 'aws.ec2.all-instance-types-names-list'
        self.INSTANCE_INFO_CACHE_KEY = 'aws.ec2.all-instance-types-data'
        self.instance_types_lock = RLock()
        self.group_name_helper = GroupNameHelper(self.context)

    def create_jwt(self, payload, secret):
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    def create_tag(self, instance_id: str, tag_key: str, tag_value: str):
        self.ec2_client.create_tags(
            Resources=[
                instance_id
            ],
            Tags=[{
                'Key': tag_key,
                'Value': tag_value
            }]
        )

    def _build_userdata(self, session: VirtualDesktopSession):
        bootstrap_context = BootstrapContext(
            config=self.context.config(),
            module_name=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
            module_id=self.context.module_id(),
            module_set=self.context.module_set(),
            base_os=session.software_stack.base_os.value,
            instance_type=session.server.instance_type
        )

        gpu_family = "NONE"
        if bootstrap_context.is_nvidia_gpu():
            gpu_family = "NVIDIA"
        elif bootstrap_context.is_amd_gpu():
            gpu_family = "AMD"

        ## Add on vdi start commands here for linux here
        rerun_on_reboot = self._retrieve_rerun_on_reboot(session.project, ScriptOSType.LINUX)
        on_vdi_start_script_commands = self._retrieve_scripts_as_commands(session.project, ScriptOSType.LINUX, ScriptEventType.ON_VDI_START)
        on_vdi_configured_script_commands = self._retrieve_scripts_as_commands(session.project, ScriptOSType.LINUX, ScriptEventType.ON_VDI_CONFIGURED)

        on_vdi_start_script_store = self._store_commands_as_linux_script(on_vdi_start_script_commands, ScriptEventType.ON_VDI_START)
        on_vdi_configured_script_store = self._store_commands_as_linux_script(on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED)

        lock_file = "/root/bootstrap/semaphore/custom_script.lock"
        instance_ready_lock_file = "/root/bootstrap/semaphore/instance_ready.lock"
        custom_script_check = [f"if [[ ! -f {lock_file} ]]; then"]
        if rerun_on_reboot:
            custom_script_check = [f"if [[ ! -f {lock_file} || -f {instance_ready_lock_file} ]]; then"]

        custom_script_commands = custom_script_check + [
            *on_vdi_start_script_store,
            *on_vdi_configured_script_store,
            f'/bin/bash scripts/virtual-desktop-host/linux/export_launch_script_env.sh -p {session.project.project_id} -o {session.owner} -n {session.project.name} -e {self.context.config().cluster_name} -c {ScriptEventType.ON_VDI_CONFIGURED.value}.sh -s {ScriptEventType.ON_VDI_START.value}.sh -r {rerun_on_reboot}',
            'source /etc/launch_script_environment',
            f'/bin/bash scripts/virtual-desktop-host/linux/{ScriptEventType.ON_VDI_START.value}.sh',
            f"echo $(date +%s) > {lock_file}",
            "fi"
        ]

        custome_broker_api_url = cluster_settings.get_setting("vdc.custom_credential_broker_api_gateway_url")

        region = self.context.config().aws_region
        jwt_token = "DefaultValue"

        try:
            secret_value = cluster_settings.get_secret("vdc.custom_credential_broker_secret_name")

            current_time = int(time.time())

            payload = {
                "region": region,
                "project_name": session.project.name,
                "session_owner": session.owner,
                "session_id": session.idea_session_id,
                "iat": current_time,
                "exp": current_time + 31536000,
                "role_arn": cluster_settings.get_setting("vdc.dcv_host_role_arn"),
                "role_session_name": f"{session.owner}-{session.idea_session_id}"
            }

            jwt_token = self.create_jwt(payload, secret_value)
        except Exception as e:
            logger.info(f"Error retriving secret from secret manager {str(e)}")

        # Check if FSx Lustre file systems are onboarded
        enable_lustre = 'true' if self._has_fsx_lustre_file_systems() else 'false'

        install_commands = custom_script_commands + [
            f'/bin/bash scripts/virtual-desktop-host/linux/install.sh -m {res_constants.MODULE_ID_VIRTUAL_DESKTOP_APP} -g {gpu_family} -u {custome_broker_api_url} -t {jwt_token} -p false -e {self.context.config().cluster_name} -n {session.project.name} -o {session.owner} -d {session.type.name} -i {session.idea_session_id} -a {region} -h {session.hibernation_enabled} -l {enable_lustre}'
        ]

        if session.software_stack.base_os == BaseOS.WINDOWS:
            change_directory_command = ['cd \"scripts\\virtual-desktop-host\\windows\"']
            on_vdi_start_script_commands = self._retrieve_scripts_as_commands(session.project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START)
            on_vdi_configured_script_commands = self._retrieve_scripts_as_commands(session.project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_CONFIGURED)
            on_vdi_start_script_store = self._store_commands_as_windows_script(on_vdi_start_script_commands, ScriptEventType.ON_VDI_START)
            on_vdi_configured_script_store = self._store_commands_as_windows_script(on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED)
            export_env_variables_commands = ['Import-Module .\\ExportLaunchScriptEnv.ps1',
                                             f'Export-EnvironmentVariables -ProjectId "{session.project.project_id}" -OwnerId "{session.owner}" -EnvName "{self.context.config().cluster_name}" -ProjectName "{session.project.name}" -OnVDIStartCommands "{ScriptEventType.ON_VDI_START.value}.ps1" -OnVDIConfigureCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"']
            on_vdi_start_script_commands = ['& .\\$env:ON_VDI_START_COMMANDS']
            install_commands = change_directory_command + export_env_variables_commands + on_vdi_start_script_store + on_vdi_configured_script_store + on_vdi_start_script_commands + [
                'Import-Module .\\Install.ps1',
                f'Install-WindowsEC2Instance -ConfigureForRESVDI -AWSRegion "{self.context.config().aws_region}" -ENVName "{self.context.config().cluster_name}" -ModuleID "{res_constants.MODULE_ID_VIRTUAL_DESKTOP_APP}" -ProjectName {session.project.name} -SessionOwner "{session.owner}" -SessionId "{session.idea_session_id}" -BootstrapToken "{jwt_token}" -CustomBrokerApi "{custome_broker_api_url}" -OnVDIConfiguredCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"'
            ]

        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        no_proxy = self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                'http_proxy': https_proxy,
                'https_proxy': https_proxy,
                'no_proxy': no_proxy
            }

        user_data_builder = BootstrapUserDataBuilder(
            base_os=session.software_stack.base_os.value,
            aws_region=self.context.config().get_string('cluster.aws.region', required=True),
            bootstrap_package_uri=cluster_settings.get_setting('cluster.installation_scripts_uri'),
            install_commands=install_commands,
            proxy_config=proxy_config,
            substitution_support=False,
            bootstrap_source_dir_path=self.context.get_bootstrap_dir()
        )

        return user_data_builder.build()

    def _has_fsx_lustre_file_systems(self) -> bool:
        """
        Check if any FSx Lustre file systems are onboarded by calling cluster manager.
        Returns True if FSx Lustre is onboarded, False otherwise.
        """
        try:
            # Use SharedFileSystemClient to list file systems
            result = self.context.shared_filesystem_client.list_onboarded_file_systems(
                ListOnboardedFileSystemsRequest()
            )
            
            # Check if any file system has fsx_lustre provider
            for fs in result.listing:
                if fs.get_provider() == constants.STORAGE_PROVIDER_FSX_LUSTRE:
                    self._logger.info(f"Found FSx Lustre file system: {fs.name}")
                    return True
            
            self._logger.info("No FSx Lustre file systems found")
            return False
            
        except Exception as e:
            self._logger.error(f"Error checking for FSx Lustre file systems: {e}")
            # Default to false if we can't determine
            return False

    def _store_commands_as_linux_script(self, commands: List[str], scriptName: ScriptEventType) -> List[str]:
        begin = "#!/bin/bash"
        script = "\n".join([begin] + commands)
        return [f'echo "{script}" > scripts/virtual-desktop-host/linux/{scriptName.value}.sh']

    def _store_commands_as_windows_script(self, commands: List[str], scriptName: ScriptEventType) -> List[str]:
        script = "`n".join(commands)
        return [f'"{script}" | Out-File -FilePath {scriptName.value}.ps1']

    def _retrieve_scripts_as_commands(self, project: Project, os_type: ScriptOSType, script_event: ScriptEventType) -> List[str]:
        scripts = project.scripts
        if not scripts:
            return []

        script_type = None
        scripts_as_commands = []
        command_prefix = ""
        if os_type == ScriptOSType.LINUX:
            script_type = scripts.linux
            boostrap_dir = "/root/bootstrap"
            command_prefix = f'/bin/bash {boostrap_dir}/latest/scripts/virtual-desktop-host/linux/download_and_execute_script.sh'
        elif os_type == ScriptOSType.WINDOWS:
            script_type = scripts.windows
            command_prefix = "Download-And-Execute-Script -uri"
            boostrap_dir = "$env:SystemDrive\\Users\\Administrator\\RES\\Bootstrap"
            scripts_as_commands.append(f'Import-Module {boostrap_dir}\\scripts\\virtual-desktop-host\\windows\\DownloadAndExecuteScript.ps1 -force')

        if not script_type:
            return []

        event_scripts = getattr(script_type, script_event.value, None)
        if not event_scripts:
            return []

        if os_type == ScriptOSType.LINUX:
            scripts_as_commands.extend([f"{command_prefix} {script.script_location} {' '.join(script.arguments or [])}" for script in event_scripts])
        elif os_type == ScriptOSType.WINDOWS:
            scripts_as_commands.extend([f"{command_prefix} {script.script_location} -arguments '{' '.join(script.arguments or [])}'" for script in event_scripts])

        return scripts_as_commands

    def _retrieve_rerun_on_reboot(self, project:Project, os_type:ScriptOSType) -> bool:
        scripts = project.scripts
        if not scripts:
            return False

        script_type = None

        if os_type == ScriptOSType.LINUX:
            script_type = scripts.linux
        elif os_type == ScriptOSType.WINDOWS:
            script_type = scripts.windows

        if not script_type:
            return False

        rerun_on_reboot = getattr(script_type, 'rerun_on_reboot', False)
        return rerun_on_reboot

    def provision_dcv_host_for_session(self, session: VirtualDesktopSession) -> dict:

        tags = {
            constants.IDEA_TAG_NAME: f'{self.context.cluster_name()}-{session.name}-{session.owner}',
            constants.IDEA_TAG_NODE_TYPE: constants.NODE_TYPE_DCV_HOST,
            constants.IDEA_TAG_ENVIRONMENT_NAME: self.context.cluster_name(),
            constants.IDEA_TAG_MODULE_ID: self.context.module_id(),
            constants.IDEA_TAG_MODULE_NAME: self.context.module_name(),
            constants.IDEA_TAG_MODULE_VERSION: self.context.module_version(),
            constants.IDEA_TAG_BACKUP_PLAN: f'{self.context.cluster_name()}-{self.context.module_id()}',
            constants.IDEA_TAG_PROJECT: session.project.name,
            constants.IDEA_TAG_DCV_SESSION_ID: 'TBD'
        }

        if Utils.is_not_empty(session.project.tags):
            for tag in session.project.tags:
                tags[tag.key] = tag.value

        custom_tags = self.context.config().get_list('global-settings.custom_tags', [])
        custom_tags_dict = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
        session_tags = Utils.convert_tags_list_of_dict_to_tags_dict(session.tags)
        tags = {
            **custom_tags_dict,
            **tags,
            **session_tags
        }

        aws_tags = []
        for key, value in tags.items():
            aws_tags.append({
                'Key': key,
                'Value': value
            })

        metadata_http_tokens = self.context.config().get_string('virtual-desktop-controller.dcv_session.metadata_http_tokens', required=True)

        kms_key_id = self.context.config().get_string('cluster.ebs.kms_key_id', required=False, default=None)
        if kms_key_id is None:
            kms_key_id = 'alias/aws/ebs'

        # Handle subnet processing for eVDI hosts

        randomize_subnet_method = self.context.config().get_bool(
            'vdc.dcv_session.network.randomize_subnets',
            default=Utils.get_as_bool(constants.DEFAULT_VDI_RANDOMIZE_SUBNETS, default=False)
        )
        subnet_autoretry_method = self.context.config().get_bool(
            'vdc.dcv_session.network.subnet_autoretry',
            default=Utils.get_as_bool(constants.DEFAULT_VDI_SUBNET_AUTORETRY, default=True)
        )
        # Determine if we have a specific list of subnets configured for VDI
        configured_vdi_subnets = self.context.config().get_list(
            'vdc.dcv_session.network.private_subnets',
            default=[]
        )
        # Required=True as these should always be available, and we want to error otherwise
        cluster_private_subnets = self.context.config().get_list(
            'cluster.network.private_subnets',
            required=True
        )

        _attempt_subnets = []
        # Use a subnet_id if specified
        if Utils.is_not_empty(session.server.subnet_id):
            # this comes in as a string from the API
            self._logger.debug(f"Using strict requested subnet_id: {session.server.subnet_id}")
            _attempt_subnets.append(session.server.subnet_id)
        elif configured_vdi_subnets:
            # A list from the config
            self._logger.debug(f"Found configured VDI subnets: {', '.join(configured_vdi_subnets)}")
            _attempt_subnets = configured_vdi_subnets
        else:

            # fallback to a list of cluster private_subnets
            self._logger.debug(f"Fallback to cluster private_subnets: {', '.join(cluster_private_subnets)}")
            _attempt_subnets = cluster_private_subnets

        # Shuffle the list if configured for random subnet
        if randomize_subnet_method:
            random.shuffle(_attempt_subnets)
            self._logger.debug(f"Applying randomize to subnet list due to configuration.")

        # At this stage _attempt_subnets contains the subnets
        # we want to attempt in the order that we prefer
        # (ordered or pre-shuffled)

        placement = {
            "Tenancy": session.software_stack.placement.tenancy if session.software_stack.placement else VirtualDesktopTenancy.DEFAULT,
        }
        if placement["Tenancy"] == VirtualDesktopTenancy.HOST:
            placement["Affinity"] = session.software_stack.placement.affinity
            if session.software_stack.placement.host_id:
                placement["HostId"] = session.software_stack.placement.host_id
            else:
                placement["HostResourceGroupArn"] = session.software_stack.placement.host_resource_group_arn

        self._logger.debug(f"Deployment Attempt Ready - Retry: {subnet_autoretry_method} Attempt_Subnets({len(_attempt_subnets)}): {', '.join(_attempt_subnets)}")

        _deployment_loop = 0
        _attempt_provision = True

        while _attempt_provision:
            _deployment_loop += 1
            # We just .pop(0) since the list has been randomized already if it was requested
            _subnet_to_try = _attempt_subnets.pop(0)
            _remainig_subnet_count = len(_attempt_subnets)

            self._logger.info(f"Deployment attempt #{_deployment_loop} subnet_id: {_subnet_to_try} Remaining Subnets: {_remainig_subnet_count}")
            if _remainig_subnet_count <= 0:
                # this is our last attempt
                self._logger.debug(f"Final deployment attempt (_remaining_subnet_count == 0)")
                _attempt_provision = False
            else:
                _attempt_provision = True

            ami_id = session.software_stack.ami_id
            if ami_id.startswith("arn:"):
                ami_id = f'resolve:ssm:{self.get_systems_manager_parameter(ami_id).get("Name")}'

            response = None

            try:
                response = self.ec2_client.run_instances(
                    UserData=self._build_userdata(session),
                    ImageId=ami_id,
                    InstanceType=session.server.instance_type,
                    TagSpecifications=[
                        {
                            'ResourceType': 'instance',
                            'Tags': aws_tags
                        }
                    ],
                    MaxCount=1,
                    MinCount=1,
                    NetworkInterfaces=[
                        {
                            'DeviceIndex': 0,
                            'AssociatePublicIpAddress': False,
                            'SubnetId': _subnet_to_try,
                            'Groups': session.server.security_groups
                        }
                    ],
                    IamInstanceProfile={
                        'Arn': session.server.instance_profile_arn
                    },
                    BlockDeviceMappings=[
                        {
                            'DeviceName': Utils.get_ec2_block_device_name(session.software_stack.base_os.value),
                            'Ebs': {
                                'DeleteOnTermination': True,
                                'VolumeSize': session.server.root_volume_size.int_val(),
                                'Encrypted': Utils.get_as_bool(constants.DEFAULT_VOLUME_ENCRYPTION_VDI, default=True),
                                'KmsKeyId': kms_key_id,
                                'VolumeType': Utils.get_as_string(constants.DEFAULT_VOLUME_TYPE_VDI, default='gp3')
                            }
                        }
                    ],
                    KeyName=session.server.key_pair_name,
                    HibernationOptions={
                        'Configured': False if Utils.is_empty(session.hibernation_enabled) else session.hibernation_enabled
                    },
                    MetadataOptions={
                        'HttpTokens': metadata_http_tokens,
                        'HttpEndpoint': 'enabled'
                    },
                    Placement=placement,
                )
            except Exception as err:
                self._logger.warning(f"Encountered Deployment Exception: {err} / Response: {response}")
                self._logger.debug(f"Remaining subnets {len(_attempt_subnets)}: {_attempt_subnets}")
                if subnet_autoretry_method and _attempt_provision:
                    self._logger.debug(f"Continue with next attempt with remaining subnets..")
                    continue
                else:
                    self._logger.warning(f"Exhausted all deployment attempts. Cannot continue with this request.")
                    raise err  # session failure reason will be shown to user

            if response:
                self._logger.debug(f"Returning response: {response}")
                return Utils.to_dict(response)

    def _add_instance_data_to_cache(self):
        with self.instance_types_lock:
            instance_type_names = self.context.cache().long_term().get(self.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY)
            instance_info_data = self.context.cache().long_term().get(self.INSTANCE_INFO_CACHE_KEY)
            if instance_type_names is None or instance_info_data is None:
                instance_type_names = []
                instance_info_data = {}

                has_more = True
                next_token = None
                while has_more:
                    if next_token is None:
                        result = self.context.aws().ec2().describe_instance_types(MaxResults=100)
                    else:
                        result = self.context.aws().ec2().describe_instance_types(MaxResults=100, NextToken=next_token)

                    next_token = Utils.get_value_as_string('NextToken', result)
                    has_more = Utils.is_not_empty(next_token)
                    current_instance_types = Utils.get_value_as_list('InstanceTypes', result)
                    for current_instance_type in current_instance_types:
                        instance_type_name = Utils.get_value_as_string('InstanceType', current_instance_type, '')
                        instance_type_names.append(instance_type_name)
                        instance_info_data[instance_type_name] = current_instance_type

                self.context.cache().long_term().set(self.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY, instance_type_names)
                self.context.cache().long_term().set(self.INSTANCE_INFO_CACHE_KEY, instance_info_data)

    def is_gpu_instance(self, instance_type: str) -> bool:
        return self.get_gpu_manufacturer(instance_type) != VirtualDesktopGPU.NO_GPU

    def get_instance_type_info(self, instance_type: str) -> Dict:
        instance_types_data = self.context.cache().long_term().get(self.INSTANCE_INFO_CACHE_KEY)
        if instance_types_data is None:
            # not found in cache, need to update it again.
            self._add_instance_data_to_cache()
            instance_types_data = self.context.cache().long_term().get(self.INSTANCE_INFO_CACHE_KEY)
        return instance_types_data[instance_type]

    def get_instance_ram(self, instance_type: str) -> SocaMemory:
        instance_info = self.get_instance_type_info(instance_type)
        return SocaMemory(
            value=Utils.get_value_as_float('SizeInMiB', Utils.get_value_as_dict('MemoryInfo', instance_info, {}), 0),
            unit=SocaMemoryUnit.MiB
        )

    def get_architecture(self, instance_type: str) -> Optional[VirtualDesktopArchitecture]:
        instance_info = self.get_instance_type_info(instance_type)
        supported_archs = Utils.get_value_as_list('SupportedArchitectures', Utils.get_value_as_dict('ProcessorInfo', instance_info, {}), [])
        for supported_arch in supported_archs:
            if supported_arch == VirtualDesktopArchitecture.ARM64.value:
                return VirtualDesktopArchitecture.ARM64
            if supported_arch == VirtualDesktopArchitecture.X86_64.value:
                return VirtualDesktopArchitecture.X86_64

    def get_gpu_manufacturer(self, instance_type: str) -> VirtualDesktopGPU:
        instance_info = self.get_instance_type_info(instance_type)
        supported_gpus = Utils.get_value_as_list('Gpus', Utils.get_value_as_dict('GpuInfo', instance_info, {}), [])
        if len(supported_gpus) == 0:
            return VirtualDesktopGPU.NO_GPU

        for supported_gpu in supported_gpus:
            if Utils.get_value_as_string('Manufacturer', supported_gpu, '').lower() == VirtualDesktopGPU.NVIDIA.lower():
                return VirtualDesktopGPU.NVIDIA
            elif Utils.get_value_as_string('Manufacturer', supported_gpu, '').lower() == VirtualDesktopGPU.AMD.lower():
                return VirtualDesktopGPU.AMD

        return VirtualDesktopGPU.NO_GPU

    def dedicated_hosts_supported(self, instance_type: str) -> bool:
        instance_info = self.get_instance_type_info(instance_type)
        return instance_info.get('DedicatedHostsSupported', False)

    def validate_min_ram(self, instance_type_name: str, software_stack: Optional[VirtualDesktopSoftwareStack]) -> bool:
        if software_stack and software_stack.min_ram > self.get_instance_ram(instance_type_name):
            # this instance doesn't have the minimum ram required to support the software stack.
            self._logger.debug(f"Software stack ({software_stack.name}) restrictions on RAM ({software_stack.min_ram}): Instance {instance_type_name} lacks enough ({self.get_instance_ram(instance_type_name)}). Skipped.")
            return False
        return True

    def get_valid_instance_types_by_allowed_list(self, hibernation_support: bool, allowed_instance_types: List[str]) -> Dict:
        instance_types_names = self.context.cache().long_term().get(self.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY)
        instance_info_data = self.context.cache().long_term().get(self.INSTANCE_INFO_CACHE_KEY)
        if instance_types_names is None or instance_info_data is None:
            # not found in cache, need to update it again.
            self._add_instance_data_to_cache()
            instance_types_names = self.context.cache().long_term().get(self.INSTANCE_TYPES_NAMES_LIST_CACHE_KEY)
            instance_info_data = self.context.cache().long_term().get(self.INSTANCE_INFO_CACHE_KEY)

        # We now have a list of all instance types (Cache has been updated IF it was empty).
        valid_instance_types_dict = {}

        allowed_instance_type_names = set()
        allowed_instance_type_families = set()
        for instance_type in allowed_instance_types:
            if '.' in instance_type:
                allowed_instance_type_names.add(instance_type)
            else:
                allowed_instance_type_families.add(instance_type)

        denied_instance_types = set(self.context.config().get_list('virtual-desktop-controller.dcv_session.instance_types.deny', default=[]))
        denied_instance_type_names = set()
        denied_instance_type_families = set()
        for instance_type in denied_instance_types:
            if '.' in instance_type:
                denied_instance_type_names.add(instance_type)
            else:
                denied_instance_type_families.add(instance_type)

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(f"get_valid_instance_types() - Instance Allow/Deny Summary")
            self._logger.debug(f"Allowed instance Families: {allowed_instance_type_families}")
            self._logger.debug(f"Allowed instances: {allowed_instance_type_names}")
            self._logger.debug(f"Denied instance Families: {denied_instance_type_families}")
            self._logger.debug(f"Denied instances: {denied_instance_type_names}")

        for instance_type_name in instance_types_names:
            instance_type_family = instance_type_name.split('.')[0]
            self._logger.debug(f"Processing - Instance Name: {instance_type_name}   Family: {instance_type_family}")

            if instance_type_name not in allowed_instance_type_names and instance_type_family not in allowed_instance_type_families:
                # instance type or instance family is not present in allow list
                self._logger.debug(f"Found {instance_type_name} ({instance_type_family}) NOT in ALLOW config: ({allowed_instance_type_names} / {allowed_instance_type_families})")
                continue

            if instance_type_name in denied_instance_type_names or instance_type_family in denied_instance_type_families:
                # instance type or instance family is present in deny list
                self._logger.debug(f"Found {instance_type_name} ({instance_type_family}) IN DENIED config: ({denied_instance_type_names} / {denied_instance_type_families})")
                continue

            instance_info = instance_info_data[instance_type_name]
            hibernation_supported = Utils.get_value_as_bool('HibernationSupported', instance_info, default=False)
            if hibernation_support and not hibernation_supported:
                self._logger.debug(f"Hibernation ({hibernation_support}) != Instance {instance_type_name} ({hibernation_supported}) Skipped.")
                continue

            # All checks passed if we make it this far
            self._logger.debug(f"Instance {instance_type_name} - Added as valid_instance_types")
            valid_instance_types_dict[instance_type_name] = instance_info
        self._logger.debug(f"Returning valid_instance_types: {valid_instance_types_dict.keys()}")
        return valid_instance_types_dict

    def get_valid_instance_types_by_software_stack(self, hibernation_support: bool, software_stack: VirtualDesktopSoftwareStack = None, gpu: VirtualDesktopGPU = None) -> List[Dict]:
        allowed_instance_types = self.context.config().get_list('virtual-desktop-controller.dcv_session.instance_types.allow', default=[])
        valid_instance_types_dict = self.get_valid_instance_types_by_allowed_list(hibernation_support, allowed_instance_types)

        if software_stack and software_stack.base_os == VirtualDesktopBaseOS.WINDOWS:
            image_info = self.describe_image_id(software_stack.ami_id)

        valid_instance_types_names = []
        valid_instance_types = []
        for instance_type_name in valid_instance_types_dict.keys():
            instance_type_family = instance_type_name.split('.')[0]
            instance_info = valid_instance_types_dict[instance_type_name]
            self._logger.debug(f"Processing - Instance Name: {instance_type_name}   Family: {instance_type_family}")
            if Utils.is_not_empty(software_stack) and software_stack.base_os == VirtualDesktopBaseOS.RHEL8 and instance_type_family == 'g4dn':
                # Disabling g4dn instances for RHEL8
                self._logger.debug(f"g4dn instances are disabled for RHEL8 instances")
                continue

            if not self.validate_min_ram(instance_type_name, software_stack):
                continue

            supported_archs = Utils.get_value_as_list('SupportedArchitectures', Utils.get_value_as_dict('ProcessorInfo', instance_info, {}), [])
            if Utils.is_not_empty(software_stack) and software_stack.architecture.value not in supported_archs:
                # not desired architecture
                self._logger.debug(f"Software Stack arch ({software_stack.architecture.value}) != Instance {instance_type_name} ({supported_archs}) Skipped.")
                continue

            if software_stack and software_stack.base_os == VirtualDesktopBaseOS.WINDOWS:
                instance_boot_modes = instance_info.get('SupportedBootModes', [])
                image_boot_mode = image_info.get('BootMode', '')
                if image_boot_mode:
                    if image_boot_mode != 'uefi-preferred' and image_boot_mode not in instance_boot_modes:
                        # image has boot mode specified and boot mode is not supported by instance
                        self._logger.debug(f"Software stack ({software_stack}) restrictions on BootMode ({image_boot_mode}): Instance {instance_type_name} doesn't support ({image_boot_mode}). Skipped.")
                        continue
                else:
                    if 'legacy-bios' not in instance_boot_modes:
                        # image has no boot mode specified and default legacy-bios is not supported by instance
                        self._logger.debug(f"Software stack ({software_stack}) restrictions on BootMode (legacy-bios): Instance {instance_type_name} doesn't support legacy-bios. Skipped.")
                        continue

            supported_gpus = Utils.get_value_as_list('Gpus', Utils.get_value_as_dict('GpuInfo', instance_info, {}), [])
            self._logger.debug(f"Instance {instance_type_name} GPU ({supported_gpus})")
            gpu_to_check_against = None
            if Utils.is_not_empty(gpu):
                gpu_to_check_against = gpu
            elif Utils.is_not_empty(software_stack):
                gpu_to_check_against = software_stack.gpu

            if gpu_to_check_against == VirtualDesktopGPU.NO_GPU:
                # we don't need GPU
                if len(supported_gpus) > 0:
                    # this instance SHOULD NOT have GPU support, but it does.
                    self._logger.debug(f"Instance {instance_type_name} Should not have GPU ({supported_gpus}) but it does.")
                    continue
            elif gpu_to_check_against is not None:
                # we need GPU
                gpu_found = False
                for supported_gpu in supported_gpus:
                    gpu_found = gpu_to_check_against.value.lower() == Utils.get_value_as_string('Manufacturer', supported_gpu, '').lower()
                    if gpu_found:
                        break

                if not gpu_found:
                    # we needed a GPU, but we didn't find any
                    self._logger.debug(f"Instance {instance_type_name} - Needed a GPU but didn't find one.")
                    continue

            if software_stack and software_stack.placement:
                if software_stack.placement.tenancy == VirtualDesktopTenancy.HOST and not self.dedicated_hosts_supported(instance_type_name):
                    self._logger.debug(f"Instance {instance_type_name} doesn't support tenancy {software_stack.placement.tenancy}. Skipped.")
                    continue

            # All checks passed if we make it this far
            self._logger.debug(f"Instance {instance_type_name} - Added as valid_instance_types for software_stack")
            valid_instance_types_names.append(instance_type_name)
            valid_instance_types.append(instance_info)
        self._logger.debug(f"Returning valid_instance_types for software_stack: {valid_instance_types_names}")
        return valid_instance_types

    def get_systems_manager_parameter(self, parameter_arn: str) -> Dict[str, Any]:
        try:
            return self.ssm_client.get_parameter(
                Name=parameter_arn,
            ).get("Parameter", {})
        except ClientError as e:
            self._logger.error(e)
            return {}

    def describe_image_id(self, ami_id: str) -> dict:
        if not ami_id:
            return {}

        if ami_id.startswith("arn:"):
            parameter = self.get_systems_manager_parameter(ami_id)
            ami_id = parameter.get("Value", "")

        try:
            response = Utils.to_dict(self.ec2_client.describe_images(
                ImageIds=[
                    ami_id
                ]
            ))
        except ClientError as e:
            self._logger.error(e)
            return {}

        images = Utils.get_value_as_list('Images', response, [])
        for image in images:
            return image
        return {}

    def create_image_for_instance_id(self, instance_id, image_name, image_description):
        if Utils.is_empty(image_name):
            image_name = f'RES-IMAGE-NAME-{instance_id}'

        if Utils.is_empty(image_description):
            image_description = f'RES-IMAGE-DESCRIPTION-{instance_id}'

        response = Utils.to_dict(self.ec2_client.create_image(
            Name=image_name,
            Description=image_description,
            InstanceId=instance_id
        ))
        return response

    def is_active_directory(self) -> bool:
        provider = self.context.config().get_string('directoryservice.provider', required=True)
        return provider in {constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY, constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}

    def change_instance_type(self, instance_id: str, instance_type_name: str) -> (str, bool):
        if Utils.is_empty(instance_id) or Utils.is_empty(instance_type_name):
            return f'Invalid {instance_id} or {instance_type_name}', False

        self._logger.info(f'Changing instance type for {instance_id} to {instance_type_name}')
        # TODO: check if server is already stopped.
        try:
            _ = self.ec2_client.modify_instance_attribute(
                InstanceId=instance_id,
                Attribute='instanceType',
                Value=instance_type_name
            )
        except Exception as e:
            self._logger.error(e)
            return repr(e), False
        return '', True
