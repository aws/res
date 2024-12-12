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
from typing import Any

import ideaclustermanager
from ideaclustermanager.app.accounts.helpers.quic_update_helper import UpdateQuicResults

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.cluster_settings import (
    ListClusterModulesResult,
    GetModuleSettingsRequest,
    GetModuleSettingsResult,
    UpdateModuleSettingsRequest,
    UpdateModuleSettingsResult,
    UpdateQuicConfigRequest,
    DescribeInstanceTypesResult,
    GetAllowedSessionsPerUserResult
)
from ideadatamodel import exceptions, constants, UpdateQuicConfigResult
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.utils import Utils

from res.utils import aws_utils
import res.constants as res_constants

from threading import RLock


class ClusterSettingsAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'ClusterSettings.ListClusterModules': {
                'scope': self.SCOPE_READ,
                'method': self.list_cluster_modules
            },
            'ClusterSettings.GetModuleSettings': {
                'scope': self.SCOPE_READ,
                'method': self.get_module_settings
            },
            'ClusterSettings.UpdateModuleSettings': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_module_settings
            },
            'ClusterSettings.DescribeInstanceTypes': {
                'scope': self.SCOPE_READ,
                'method': self.describe_instance_types
            },
            'ClusterSettings.GetAllowedSessionsPerUser': {
                'scope': self.SCOPE_READ,
                'method': self.get_allowed_sessions_per_user
            },
            'ClusterSettings.UpdateQuicConfig': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_quic
            }
        }

        self.config: ClusterConfig = self.context.config()

        self.instance_types_lock = RLock()

    def list_cluster_modules(self, context: ApiInvocationContext):
        cluster_modules = self.context.get_cluster_modules()
        context.success(ListClusterModulesResult(
            listing=cluster_modules
        ))

    def get_module_settings(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetModuleSettingsRequest)

        module_id = request.module_id
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('module_id is required')
        
        if not self.context.config().get_bool('bastion-host.public') and module_id == constants.MODULE_BASTION_HOST:
            context.success(GetModuleSettingsResult(
                settings={
                    "public": False
                }
            ))
            return

        module_config = self.context.config().get_config(module_id, module_id=module_id).as_plain_ordered_dict()

        if module_id == constants.MODULE_DIRECTORYSERVICE:
            if res_constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY in module_config:
                module_config[res_constants.SERVICE_ACCOUNT_USER_DN_KEY] = aws_utils.get_secret_string(module_config[res_constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY])

        if not context.is_administrator() and module_id in constants.RESTRICTED_MODULES_FOR_NON_ADMINS:
            filtered_config = {}
            for key, value in module_config.items():
                if key in constants.RESTRICTED_MODULE_NON_ADMIN_PARENT_KEYS[module_id]:
                    filtered_config[key] = value
            module_config = filtered_config

        context.success(GetModuleSettingsResult(
            settings=module_config
        ))

    def update_module_settings(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateModuleSettingsRequest)

        module_id = request.module_id
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('module_id is required')
        if type(request.settings) is not dict:
            raise exceptions.invalid_params('invalid settings')

        settings = Utils.flatten_dict(request.settings)
        if len(settings) > 100:
            raise exceptions.invalid_params('only 100 settings can be updated at once')

        if res_constants.SERVICE_ACCOUNT_USER_DN_KEY in settings:
            # Create a secret ARN for service account user DN to avoid storing sensitive data in DDB
            settings[f"{res_constants.SERVICE_ACCOUNT_USER_DN_KEY}_secret_arn"] = aws_utils.create_or_update_secret(
                self.config.cluster_name, module_id,
                res_constants.SERVICE_ACCOUNT_USER_DN_INPUT_PARAMETER_NAME,
                settings[res_constants.SERVICE_ACCOUNT_USER_DN_KEY]
            )
            settings.pop(res_constants.SERVICE_ACCOUNT_USER_DN_KEY)

        self.config.db.transact_set_cluster_settings(module_id, settings)
        for setting in settings:
            self.config.put(f'{module_id}.{setting}', settings[setting])

        context.success(UpdateModuleSettingsResult())

    def describe_instance_types(self, context: ApiInvocationContext):

        instance_types = self.context.cache().long_term().get('aws.ec2.all-instance-types')
        if instance_types is None:
            with self.instance_types_lock:

                instance_types = self.context.cache().long_term().get('aws.ec2.all-instance-types')
                if instance_types is None:
                    instance_types = []
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
                        if len(current_instance_types) > 0:
                            instance_types += current_instance_types

                    self.context.cache().long_term().set('aws.ec2.all-instance-types', instance_types)

        context.success(DescribeInstanceTypesResult(
            instance_types=instance_types
        ))

    def get_allowed_sessions_per_user(self, context: ApiInvocationContext):
        allowed_sessions_per_user = self.config.db.get_config_entry("vdc.dcv_session.allowed_sessions_per_user")

        context.success(GetAllowedSessionsPerUserResult(allowed_sessions_per_user=Utils.get_value_as_int("value", allowed_sessions_per_user, 0)))

    def update_quic(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateQuicConfigRequest)
        enable_quic = request.enable
        result = self.context.accounts.update_quic(enable_quic)
        quic_action = "enabling" if enable_quic else "disabling"
        if result == UpdateQuicResults.SUCCESS:
            context.success(UpdateQuicConfigResult())
        elif result == UpdateQuicResults.ROLLBACK_COMPLETE:
            context.fail(
                error_code=result,
                payload=UpdateQuicConfigResult(),
                message=f"Error while {quic_action} QUIC, rollback was successful."
            )
        else:
            context.fail(
                error_code=result,
                payload=UpdateQuicConfigResult(),
                message=f"Error while {quic_action} QUIC, rollback was unsuccessful."
            )

    def _update_config_entry(self, key: str, value: Any):
        module_id = self.config.get_module_id(constants.MODULE_CLUSTER_MANAGER)
        self.config.db.set_config_entry(f'{module_id}.{key}', value)
        self.config.put(f'{module_id}.{key}', value)

    def _update_config_entry_vdc(self, key: str, value: Any):
        module_id = self.config.get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)
        self.config.db.set_config_entry(f'{module_id}.{key}', value)
        self.config.put(f'{module_id}.{key}', value)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])
        is_authenticated_user = context.is_authenticated_user()

        if is_authorized:
            acl_entry['method'](context)
            return

        if is_authenticated_user and namespace in (
            'ClusterSettings.ListClusterModules',
            'ClusterSettings.GetModuleSettings',
            'ClusterSettings.DescribeInstanceTypes'
        ):
            acl_entry['method'](context)
            return

        raise exceptions.unauthorized_access()
