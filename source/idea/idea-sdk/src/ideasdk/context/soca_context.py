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

from ideadatamodel import (
    locale, constants, exceptions, SocaBaseModel
)

import ideasdk
from ideasdk.protocols import (
    SocaContextProtocol, CacheProviderProtocol, SocaPubSubProtocol,
    SocaServiceRegistryProtocol, SocaConfigType
)
from ideasdk.service import SocaServiceRegistry
from ideasdk.aws import (
    AWSClientProviderOptions, AwsClientProvider, IamPermissionUtil,
    InstanceMetadataUtil, AWSUtil, AwsServiceEndpoint
)

from ideasdk.logging import SocaLogging
from ideasdk.pubsub import SocaPubSub
from ideasdk.cache import CacheProvider
from ideasdk.utils import Utils, EnvironmentUtils
from ideasdk.config.soca_config import SocaConfig
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.distributed_lock import DistributedLock
from ideasdk.clustering import LeaderElection
from ideasdk.metrics import MetricsService

from logging import Logger
from typing import Optional, List, Dict, Any
from threading import RLock


class SocaContextOptions(SocaBaseModel):
    cluster_name: Optional[str]
    aws_region: Optional[str]
    aws_profile: Optional[str]
    module_name: Optional[str]
    module_id: Optional[str]
    module_set: Optional[str]

    enable_metrics: Optional[bool]
    metrics_namespace: Optional[str]

    enable_iam_permission_util: Optional[bool]
    enable_instance_metadata_util: Optional[bool]
    enable_aws_util: Optional[bool]
    enable_aws_client_provider: Optional[bool]
    enable_distributed_lock: Optional[bool]
    enable_leader_election: Optional[bool]

    is_app_server: Optional[bool]

    # if set to True, AwsClientProvider will be initialized with Vpc Endpoint configuration, if enabled and available.
    use_vpc_endpoints: Optional[bool]

    default_logging_profile: Optional[str]
    locale: Optional[str]

    config: Optional[Dict[str, Any]]

    @staticmethod
    def default() -> 'SocaContextOptions':
        return SocaContextOptions(
            cluster_name=None,
            enable_metrics=False,
            enable_iam_permission_util=False,
            enable_instance_metadata_util=False,
            enable_aws_util=False,
            enable_aws_client_provider=False,
            is_app_server=False,
            default_logging_profile=None,
            locale=None,
            use_vpc_endpoints=False,
            enable_distributed_lock=False,
            enable_leader_election=False,
            config=None
        )


class SocaContext(SocaContextProtocol):

    def __init__(self, options: SocaContextOptions = None):

        try:

            self._lock = RLock()

            if options is None:
                options = SocaContextOptions.default()

            self._options = options
            self._config: Optional[SocaConfigType] = None
            self._aws: Optional[AwsClientProvider] = None
            self._permission_util: Optional[IamPermissionUtil] = None
            self._instance_metadata_util: Optional[InstanceMetadataUtil] = None
            self._aws_util: Optional[AWSUtil] = None
            self._distributed_lock: Optional[DistributedLock] = None
            self._metrics_service: Optional[MetricsService] = None
            self._leader_election: Optional[LeaderElection] = None

            is_app_server = Utils.get_as_bool(options.is_app_server, False)
            if is_app_server:

                if Utils.is_empty(options.cluster_name):
                    raise exceptions.invalid_params('cluster_name is required')
                if Utils.is_empty(options.aws_region):
                    raise exceptions.invalid_params('aws_region is required')
                if Utils.is_empty(options.module_id):
                    raise exceptions.invalid_params('module_id is required')
                if Utils.is_empty(options.module_set):
                    raise exceptions.invalid_params('module_set is required')

                self._config = ClusterConfig(
                    cluster_name=options.cluster_name,
                    aws_region=options.aws_region,
                    module_id=options.module_id,
                    module_set=options.module_set,
                    aws_profile=options.aws_profile,
                    create_subscription=True
                )

                self._logging = SocaLogging(config=self._config, module_id=options.module_id)
                self._cache_provider = CacheProvider(context=self, module_id=options.module_id)

                self._config.set_logger(self._logging.get_logger('cluster-config'))

            elif options.config is None and Utils.is_not_empty(options.cluster_name) and Utils.is_not_empty(options.aws_region):

                self._config = ClusterConfig(
                    cluster_name=options.cluster_name,
                    aws_region=options.aws_region,
                    module_id=options.module_id,
                    module_set=options.module_set,
                    aws_profile=options.aws_profile
                )

                self._logging = SocaLogging(default_logging_profile=self._options.default_logging_profile)
                self._cache_provider = CacheProvider(context=self, module_id='default')

            else:

                config = Utils.get_as_dict(options.config, {})
                self._config = SocaConfig(config)
                self._logging = SocaLogging(module_id='default', default_logging_profile=self._options.default_logging_profile)
                self._cache_provider = CacheProvider(context=self, module_id='default')

            # soca sdk defaults
            self._broadcast = SocaPubSub(
                topic=constants.TOPIC_BROADCAST,
                logger=self._logging.get_logger()
            )
            self._service_registry = SocaServiceRegistry(context=self)

            # begin: optional components
            if options.enable_aws_client_provider:
                endpoints = []
                if Utils.is_true(options.use_vpc_endpoints) and self.config().get_bool('cluster.network.use_vpc_endpoints', False):
                    vpc_endpoints = self.config().get_config('cluster.network.vpc_interface_endpoints', {})
                    for service_name in vpc_endpoints:
                        endpoint_config = vpc_endpoints[service_name]
                        if not Utils.get_value_as_bool('enabled', endpoint_config, False):
                            continue
                        endpoint_url = Utils.get_value_as_string('endpoint_url', endpoint_config)
                        if Utils.is_empty(endpoint_url):
                            continue
                        endpoints.append(AwsServiceEndpoint(
                            service_name=service_name,
                            endpoint_url=endpoint_url
                        ))

                self._aws = AwsClientProvider(
                    options=AWSClientProviderOptions(
                        profile=options.aws_profile,
                        region=options.aws_region,
                        endpoints=endpoints
                    )
                )

            # initialize locale
            if Utils.is_not_empty(self._options.locale):
                self._locale = self._options.locale
            else:
                self._locale = self.config().get_string('cluster.locale', EnvironmentUtils.get_environment_variable('LC_CTYPE', default='en_US'))
            locale.init(self._locale)

            # iam permission utils
            if options.enable_iam_permission_util:
                self._permission_util = IamPermissionUtil(context=self)

            # ec2 instance metadata util
            if options.enable_instance_metadata_util:
                self._instance_metadata_util = InstanceMetadataUtil()

            # aws util
            if options.enable_aws_util:
                self._aws_util = AWSUtil(context=self)

            # distributed lock
            if options.enable_distributed_lock:
                self._distributed_lock = DistributedLock(context=self)

            # leader election
            if options.enable_leader_election:
                self._leader_election = LeaderElection(context=self)

            # metrics
            if options.enable_metrics:
                self._metrics_service = MetricsService(context=self, default_namespace=options.metrics_namespace)

        except BaseException as e:
            if self._distributed_lock is not None:
                self._distributed_lock.stop()
            if self._leader_election is not None:
                self._leader_election.stop()
            if self._metrics_service is not None:
                self._metrics_service.stop()
            if self._config is not None and isinstance(self._config, ClusterConfig):
                self._config.db.stop()
            raise e

    def logging(self) -> SocaLogging:
        return self._logging

    def logger(self, name=None) -> Logger:
        return self.logging().get_logger(name)

    @property
    def locale(self) -> str:
        return self._locale

    @property
    def currency_code(self) -> str:
        return locale.get_currency_code()

    @property
    def currency_symbol(self) -> str:
        return locale.get_currency_symbol()

    def config(self) -> SocaConfigType:
        return self._config

    def get_cluster_modules(self) -> List[Dict]:
        if isinstance(self._config, ClusterConfig):
            return self._config.db.get_cluster_modules()
        else:
            return []

    def get_cluster_module_info(self, module_id: str) -> Optional[Dict]:
        if isinstance(self._config, ClusterConfig):
            return self._config.db.get_module_info(module_id)
        else:
            return None

    def encoding(self):
        return self.config().get_string('cluster.encoding', 'utf-8')

    def cluster_name(self) -> Optional[str]:
        return self.config().get_string('cluster.cluster_name')

    def module_set(self) -> Optional[str]:
        return self._options.module_set

    def module_name(self) -> Optional[str]:
        return self._options.module_name

    def module_id(self) -> Optional[str]:
        return self._options.module_id

    def module_version(self) -> Optional[str]:
        return ideasdk.__version__

    def cluster_timezone(self) -> str:
        return self.config().get_string('cluster.timezone', default='America/Los_Angeles')

    def get_aws_solution_id(self) -> str:
        return constants.AWS_SOLUTION_ID

    def get_cluster_home_dir(self) -> Optional[str]:
        return self.config().get_string('cluster.home_dir')

    def aws(self) -> AwsClientProvider:
        return self._aws

    def cache(self) -> CacheProviderProtocol:
        return self._cache_provider

    def service_registry(self) -> SocaServiceRegistryProtocol:
        return self._service_registry

    def broadcast(self) -> SocaPubSubProtocol:
        return self._broadcast

    def iam_permission_util(self) -> IamPermissionUtil:
        return self._permission_util

    def ec2_metadata_util(self) -> InstanceMetadataUtil:
        return self._instance_metadata_util

    def aws_util(self) -> AWSUtil:
        return self._aws_util

    def distributed_lock(self) -> DistributedLock:
        return self._distributed_lock

    def is_leader(self) -> bool:
        if self._leader_election is None:
            return True
        return self._leader_election.is_leader()
