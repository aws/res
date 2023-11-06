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

from ideadatamodel import exceptions, constants
from ideasdk.utils import Utils
from ideasdk.config.cluster_config_db import ClusterConfigDB
from ideasdk.config.soca_config import SocaConfig
from ideasdk.dynamodb.dynamodb_stream_subscriber import DynamoDBStreamSubscriber

from typing import Optional, List, Dict, Any
from pyhocon import ConfigTree


class ClusterConfig(SocaConfig, DynamoDBStreamSubscriber):
    """
    Cluster Config
    extends SocaConfig to provide functionality on top of configuration entries saved in cluster config ddb tables
    """

    def __init__(self, cluster_name: str,
                 aws_region: str,
                 module_id: Optional[str] = None,
                 module_set: Optional[str] = None,
                 aws_profile: Optional[str] = None,
                 create_subscription: bool = False,
                 logger=None):

        if Utils.is_empty(cluster_name):
            raise exceptions.invalid_params('cluster_name is required')
        if Utils.is_empty(aws_region):
            raise exceptions.invalid_params('aws_region is required')

        if Utils.is_empty(module_set):
            module_set = 'default'

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.logger = logger

        self.module_info = None
        self.db = ClusterConfigDB(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            create_subscription=create_subscription,
            cluster_config_subscriber=self,
            logger=logger
        )

        self.module_set = module_set
        self.module_id: Optional[str] = None
        self.module_info: Optional[Dict] = None
        if not Utils.is_empty(module_id):
            self.set_module_id(module_id)

        config = self.db.build_config_from_db()

        super().__init__(config=config.as_dict())

    def set_logger(self, logger):
        self.logger = logger
        self.db.set_logger(logger)

    def get_module_id(self, module_name: str) -> str:
        return super().get_string(f'global-settings.module_sets.{self.module_set}.{module_name}.module_id', required=True)

    def set_module_id(self, module_id: str):
        module_info = self.db.get_module_info(module_id)
        if module_info is None:
            raise exceptions.general_exception(f'module not found for module_id: {module_id}')
        self.module_id = module_id
        self.module_info = module_info

    def is_module_enabled(self, module_name: str) -> bool:
        module_id = super().get_string(f'global-settings.module_sets.{self.module_set}.{module_name}.module_id')
        return Utils.is_not_empty(module_id)

    def get_real_key(self, key: str, module_id: str = None) -> str:
        module_name = key.split('.')[0]

        if module_name == 'global-settings':
            return key

        if Utils.is_empty(module_id):
            if self.module_info is not None and self.module_info['name'] == module_name:
                # this condition is to retrieve the module mapping for a module that IS the current module
                # example. VDC needs access to VDC Config (for my current module id)
                module_id = self.module_info['module_id']
            else:
                # this condition is to retrieve the module mapping for a module that isn't the current module
                # example. VDC needs access to scheduler configs. It will go via this condition.
                module_id = super().get_string(f'global-settings.module_sets.{self.module_set}.{module_name}.module_id')

        if Utils.is_empty(module_id):
            # this condition is for CUSTOM SETTINGS that the customer might add
            module_id = module_name

        return f'{module_id}.{".".join(key.split(".")[1:])}'

    def get(self, key: str, default=None, required=False, module_id=None) -> Optional[Any]:
        return super().get(self.get_real_key(key, module_id), default, required)

    def get_string(self, key, default=None, required=False, module_id=None) -> Optional[str]:
        return super().get_string(self.get_real_key(key, module_id), default, required)

    def get_int(self, key, default=None, required=False, module_id=None) -> Optional[int]:
        return super().get_int(self.get_real_key(key, module_id), default, required)

    def get_float(self, key, default=None, required=False, module_id=None) -> Optional[float]:
        return super().get_float(self.get_real_key(key, module_id), default, required)

    def get_bool(self, key, default=None, required=False, module_id=None) -> Optional[bool]:
        return super().get_bool(self.get_real_key(key, module_id), default, required)

    def get_list(self, key, default=None, required=False, module_id=None) -> Optional[List]:
        return super().get_list(self.get_real_key(key, module_id), default, required)

    def get_config(self, key, default=None, required=False, module_id=None) -> Optional[ConfigTree]:
        return super().get_config(self.get_real_key(key, module_id), default, required)

    def get_secret(self, key, default=None, required=False, module_id=None) -> Optional[str]:
        secret_arn = self.get_string(key, default, required, module_id)
        if Utils.is_empty(secret_arn):
            return None
        response = self.db.aws.secretsmanager().get_secret_value(
            SecretId=secret_arn
        )
        return Utils.get_value_as_string('SecretString', response)

    def on_create(self, entry: Dict):
        log_message = f'config created: {Utils.to_json(entry)}'
        if self.logger is not None:
            self.logger.info(log_message)
        else:
            print(log_message)
        key = entry['key']
        value = entry.get('value')
        super().put(key, value)

    def on_update(self, old_entry: Dict, new_entry: Dict):
        log_message = f'config updated: old - {Utils.to_json(old_entry)}, new - {new_entry}'
        if self.logger is not None:
            self.logger.info(log_message)
        else:
            print(log_message)
        key = new_entry['key']
        value = new_entry.get('value')
        super().put(key, value)

    def on_delete(self, entry: Dict):
        log_message = f'config deleted: {Utils.to_json(entry)}'
        if self.logger is not None:
            self.logger.info(log_message)
        else:
            print(log_message)
        key = entry['key']
        super().pop(key)

    def get_cluster_external_endpoint(self) -> str:
        cluster_module_id = self.get_module_id(constants.MODULE_CLUSTER)
        external_alb_dns = self.get_string(f'{cluster_module_id}.load_balancers.external_alb.certificates.custom_dns_name', default=None)
        if Utils.is_empty(external_alb_dns):
            external_alb_dns = self.get_string(f'{cluster_module_id}.load_balancers.external_alb.load_balancer_dns_name', default=None)
        if Utils.is_empty(external_alb_dns):
            raise exceptions.cluster_config_error('cluster external endpoint not found')
        return f'https://{external_alb_dns}'

    def get_cluster_internal_endpoint(self) -> str:
        cluster_module_id = self.get_module_id(constants.MODULE_CLUSTER)

        internal_alb_dns = self.get_string(f'{cluster_module_id}.load_balancers.internal_alb.certificates.custom_dns_name', default=None)
        if Utils.is_empty(internal_alb_dns):
            # backward compat. custom_dns_name moved under certificates starting with 3.0.0-rc.2
            internal_alb_dns = self.get_string(f'{cluster_module_id}.load_balancers.internal_alb.custom_dns_name', default=None)

        if Utils.is_empty(internal_alb_dns):
            internal_alb_dns = self.get_string(f'{cluster_module_id}.load_balancers.internal_alb.load_balancer_dns_name', default=None)
        if Utils.is_empty(internal_alb_dns):
            raise exceptions.cluster_config_error('cluster internal endpoint not found')
        return f'https://{internal_alb_dns}'
