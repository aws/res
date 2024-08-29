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

from __future__ import annotations

from ideasdk.config.soca_config import SocaConfig
from ideadatamodel import (
    CustomFileLoggerParams,
    EC2InstanceType,
    AutoScalingGroup,
    CloudFormationStack,
    CloudFormationStackResources,
    EC2Instance,
    EC2SpotFleetRequestConfig,
    EC2SpotFleetInstance,
    EC2InstanceIdentityDocument,
    EC2InstanceUnitPrice,
    AwsProjectBudget,
    SocaJob,
    AuthResult
)
from ideadatamodel.api.api_model import ApiAuthorization

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List, Callable, Any, Union, Hashable, Set, TypeVar
from logging import Logger
from cacheout import Cache
import warnings
import functools

SubscriptionListener = Callable[..., Any]
PagingCallback = Callable[..., Any]
CacheTTL = Union[int, float]
T = TypeVar('T')
SocaConfigType = TypeVar('SocaConfigType', bound=SocaConfig)
SocaContextProtocolType = TypeVar('SocaContextProtocolType', bound='SocaContextProtocol')


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                      category=DeprecationWarning,
                      stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return new_func


class SocaBaseProtocol(ABC):
    ...


class SocaPubSubProtocol(SocaBaseProtocol):

    @abstractmethod
    def publish(self, sender: str, **kwargs):
        ...

    @abstractmethod
    def subscribe(self, listener: SubscriptionListener, sender: Optional[str]):
        ...

    @abstractmethod
    def unsubscribe(self, listener: SubscriptionListener, sender: Optional[str] = None):
        ...


class AwsClientProviderProtocol(SocaBaseProtocol):

    @abstractmethod
    def aws_partition(self) -> str:
        ...

    @abstractmethod
    def aws_region(self) -> str:
        ...

    @abstractmethod
    def aws_account_id(self) -> str:
        ...

    @abstractmethod
    def aws_dns_suffix(self) -> str:
        ...

    @abstractmethod
    def aws_profile(self) -> str:
        ...

    @abstractmethod
    def instance_metadata(self) -> InstanceMetadataUtilProtocol:
        ...

    @abstractmethod
    def is_running_in_ec2(self) -> bool:
        ...

    @abstractmethod
    def are_credentials_expired(self) -> bool:
        ...

    @abstractmethod
    def supported_clients(self) -> List[str]:
        ...

    @abstractmethod
    def get_client(self, service_name: str, **kwargs):
        ...

    @abstractmethod
    def s3(self):
        ...

    @abstractmethod
    def ec2(self):
        ...

    @abstractmethod
    def elbv2(self):
        ...

    @abstractmethod
    def iam(self):
        ...

    @abstractmethod
    def cloudformation(self):
        ...

    @abstractmethod
    def autoscaling(self):
        ...

    @abstractmethod
    def secretsmanager(self):
        ...

    @abstractmethod
    def budgets(self):
        ...

    @abstractmethod
    def ses(self, region_name: str = None):
        ...

    @abstractmethod
    def service_quotas(self):
        ...

    @abstractmethod
    def pricing(self):
        ...

    @abstractmethod
    def cloudwatch(self):
        ...

    @abstractmethod
    def efs(self):
        ...

    @abstractmethod
    def fsx(self):
        ...

    @abstractmethod
    def ds(self):
        ...

    @abstractmethod
    def es(self):
        ...

    @abstractmethod
    def sts(self):
        ...

    @abstractmethod
    def acm(self):
        ...

    @abstractmethod
    def dynamodb(self):
        ...

    @abstractmethod
    def dynamodb_table(self):
        ...

    @abstractmethod
    def cognito_idp(self):
        ...

    @abstractmethod
    def kinesis(self):
        ...

    @abstractmethod
    def resource_groups_tagging_api(self):
        ...

    @abstractmethod
    def backup(self):
        ...


AwsClientProviderType = TypeVar('AwsClientProviderType', bound=AwsClientProviderProtocol)


class SocaCacheProtocol(SocaBaseProtocol):

    @property
    @abstractmethod
    def cache_backend(self) -> Optional[Cache]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def size_in_bytes(self) -> int:
        ...

    @property
    @abstractmethod
    def size(self) -> int:
        ...

    @abstractmethod
    def get(self, key: Hashable, default: Any = None) -> Any:
        ...

    @abstractmethod
    def set(self, key: Hashable, value: Any, ttl: Optional[CacheTTL] = None) -> None:
        ...

    @abstractmethod
    def delete(self, key: Hashable) -> int:
        ...


class CacheProviderProtocol(SocaBaseProtocol):

    @abstractmethod
    def long_term(self) -> SocaCacheProtocol:
        ...

    @abstractmethod
    def short_term(self) -> SocaCacheProtocol:
        ...

    @abstractmethod
    def reload(self, name: str = None) -> SocaCacheProtocol:
        ...


class SocaLoggingProtocol(SocaBaseProtocol):

    def get_log_dir(self) -> str:
        ...

    def get_logger(self, logger_name: str = None) -> Logger:
        ...

    def get_custom_file_logger(self, params: CustomFileLoggerParams) -> Logger:
        ...


class MetricsAccumulatorProtocol(SocaBaseProtocol):

    @property
    @abstractmethod
    def accumulator_id(self):
        ...

    @abstractmethod
    def publish_metrics(self) -> None:
        ...


class MetricsServiceProtocol(SocaBaseProtocol):

    @abstractmethod
    def publish(self, metric_data: List[Dict]):
        ...

    @abstractmethod
    def register_accumulator(self, accumulator: MetricsAccumulatorProtocol):
        ...

    @abstractmethod
    def start(self):
        ...

    @abstractmethod
    def stop(self):
        ...


class IamPermissionUtilProtocol(SocaBaseProtocol):

    @abstractmethod
    def has_permission(self, action_names: List[str],
                       resource_arns: List[str] = None,
                       context_entries: List[Dict] = None) -> bool:
        ...


class InstanceMetadataUtilProtocol(SocaBaseProtocol):

    def get_imds_auth_token(self) -> str:
        ...

    def get_imds_auth_header(self) -> str:
        ...

    def is_running_in_ec2(self) -> bool:
        ...

    @abstractmethod
    def get_instance_identity_document(self) -> EC2InstanceIdentityDocument:
        ...

    @abstractmethod
    def get_iam_security_credentials(self) -> str:
        ...


class AWSUtilProtocol(SocaBaseProtocol):

    @staticmethod
    @abstractmethod
    def get_instance_type_class(instance_type: str) -> Tuple[str, bool]:
        ...

    @abstractmethod
    def get_all_instance_types(self) -> Set[str]:
        ...

    @abstractmethod
    def get_instance_types_for_class(self, instance_class: str) -> List[str]:
        ...

    @abstractmethod
    def get_ec2_instance_type(self, instance_type: str) -> EC2InstanceType:
        ...

    @abstractmethod
    def is_instance_type_valid(self, instance_type: str) -> bool:
        ...

    @abstractmethod
    def is_instance_type_efa_supported(self, instance_type: str) -> bool:
        ...

    @abstractmethod
    def s3_bucket_has_access(self, bucket_name: str) -> Dict:
        ...

    @abstractmethod
    def invoke_aws_listing(self, fn: Callable, result_cb: Callable[..., List[T]], max_results: int = 1000,
                           marker_based_paging=False, **result_cb_kwargs) -> List[T]:
        ...

    @abstractmethod
    def ec2_describe_instances(self, filters: list = None, page_size: int = None,
                               paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:
        ...

    @abstractmethod
    def ec2_describe_compute_instances(self, instance_states: Optional[List[str]], page_size: int = None,
                                       paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:
        ...

    @abstractmethod
    def ec2_describe_dcv_instances(self, instance_states: Optional[List[str]], page_size: int = None,
                                   paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:
        ...

    @abstractmethod
    def ec2_describe_spot_fleet_request(self, spot_fleet_request_id: str) -> Optional[EC2SpotFleetRequestConfig]:
        ...

    @abstractmethod
    def ec2_modify_spot_fleet_request(self, spot_fleet_request_id: str, target_capacity: int):
        ...

    @abstractmethod
    def ec2_describe_spot_fleet_instances(self,
                                          spot_fleet_request_id: str, page_size: Optional[int],
                                          max_results: Optional[int],
                                          paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2SpotFleetInstance]]:
        ...

    @abstractmethod
    def ec2_terminate_instances(self, instance_ids: List[str]):
        ...

    @abstractmethod
    def ec2_describe_reserved_instances(self, instance_types: List[str]) -> Optional[Dict[str, int]]:
        ...

    @abstractmethod
    def cloudformation_describe_stack(self, stack_name: str) -> Optional[CloudFormationStack]:
        ...

    @abstractmethod
    def cloudformation_describe_stack_resources(self, stack_name: str) -> Optional[CloudFormationStackResources]:
        ...

    @abstractmethod
    def cloudformation_delete_stack(self, stack_name: str):
        ...

    @abstractmethod
    def autoscaling_update_auto_scaling_group(self, auto_scaling_group_name: str, desired_capacity: int,
                                              min_size: Optional[int] = None,
                                              max_size: Optional[int] = None):
        ...

    @abstractmethod
    def autoscaling_describe_auto_scaling_group(self, auto_scaling_group_name: str) -> Optional[AutoScalingGroup]:
        ...

    @abstractmethod
    def autoscaling_detach_instances(self, auto_scaling_group_name: str, instance_ids: List[str],
                                     decrement_desired_capacity: bool = False):
        ...

    @abstractmethod
    def is_security_group_valid(self, security_group_id: str) -> bool:
        ...

    @abstractmethod
    def get_instance_profile_arn(self, instance_profile_name: str) -> Dict:
        ...

    @abstractmethod
    def get_purchased_ri_count(self, instance_type: str) -> int:
        ...

    @abstractmethod
    def get_ec2_instance_type_unit_price(self, instance_type: str) -> EC2InstanceUnitPrice:
        ...

    @abstractmethod
    def budgets_get_budget(self, budget_name: str) -> Optional[AwsProjectBudget]:
        ...

    @abstractmethod
    def get_soca_job_from_stack(self, stack_name: str) -> Optional[SocaJob]:
        ...

    @abstractmethod
    def handle_aws_exception(self, e):
        ...

    @abstractmethod
    def create_s3_presigned_url(self, key: str, expires_in=3600) -> str:
        ...

    @abstractmethod
    def dynamodb_check_table_exists(self, table_name: str, wait: bool = False) -> bool:
        ...

    @abstractmethod
    def dynamodb_create_table(self, create_table_request: Dict, wait: bool = False, ttl: bool = False, ttl_attribute_name: str = None) -> bool:
        ...


class SocaContextProtocol(SocaBaseProtocol):

    @property
    @abstractmethod
    def locale(self) -> str:
        ...

    @abstractmethod
    def logging(self) -> SocaLoggingProtocol:
        ...

    @abstractmethod
    def logger(self, name=None) -> Logger:
        ...

    @abstractmethod
    def config(self) -> SocaConfigType:
        ...

    @abstractmethod
    def encoding(self):
        ...

    @abstractmethod
    def cluster_name(self) -> str:
        ...

    @abstractmethod
    def module_set(self) -> Optional[str]:
        ...

    @abstractmethod
    def module_name(self) -> str:
        ...

    @abstractmethod
    def module_id(self) -> str:
        ...

    @abstractmethod
    def module_version(self) -> str:
        ...

    @abstractmethod
    def cluster_timezone(self) -> str:
        ...

    @abstractmethod
    def get_aws_solution_id(self) -> str:
        ...

    @abstractmethod
    def get_cluster_home_dir(self) -> str:
        ...

    @abstractmethod
    def aws(self) -> Optional[AwsClientProviderType]:
        ...

    @abstractmethod
    def cache(self) -> Optional[CacheProviderProtocol]:
        ...

    @abstractmethod
    def service_registry(self) -> SocaServiceRegistryProtocol:
        ...

    @abstractmethod
    def broadcast(self) -> SocaPubSubProtocol:
        ...

    @abstractmethod
    def iam_permission_util(self) -> IamPermissionUtilProtocol:
        ...

    @abstractmethod
    def ec2_metadata_util(self) -> InstanceMetadataUtilProtocol:
        ...

    @abstractmethod
    def aws_util(self) -> AWSUtilProtocol:
        ...

    @abstractmethod
    def get_cluster_modules(self) -> List[Dict]:
        ...

    @abstractmethod
    def get_cluster_module_info(self, module_id: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def distributed_lock(self) -> DistributedLockProtocol:
        ...

    @abstractmethod
    def is_leader(self) -> bool:
        ...


class SocaServiceProtocol(SocaBaseProtocol):

    @abstractmethod
    def service_id(self) -> str:
        ...

    @abstractmethod
    def start(self):
        ...

    @abstractmethod
    def stop(self):
        ...

    def on_broadcast(self, message: str):
        ...

    def is_running(self) -> bool:
        ...


class SocaServiceRegistryProtocol(SocaBaseProtocol):

    @abstractmethod
    def register(self, service: SocaServiceProtocol):
        ...

    @abstractmethod
    def get_service(self, service_id: str) -> Optional[SocaServiceProtocol]:
        ...

    @abstractmethod
    def services(self):
        ...


class MetricsProviderProtocol(SocaBaseProtocol):

    @abstractmethod
    def log(self, metric_data: List[Dict]):
        ...

    @abstractmethod
    def flush(self):
        ...


class MetricsProviderFactoryProtocol(SocaBaseProtocol):

    @abstractmethod
    def get_provider(self, namespace: str) -> MetricsProviderProtocol:
        ...


class ApiInvocationContextProtocol(SocaBaseProtocol):

    @property
    @abstractmethod
    def request(self) -> Dict:
        ...

    @property
    @abstractmethod
    def response(self) -> Dict:
        ...

    @property
    @abstractmethod
    def namespace(self) -> str:
        ...

    @property
    @abstractmethod
    def context(self) -> SocaContextProtocolType:
        ...


class ApiAuthorizationServiceProtocol(SocaBaseProtocol):
    
    @abstractmethod
    def get_authorization(self, decoded_token: Optional[Dict]) -> Optional[ApiAuthorization]:
        ...

    @abstractmethod
    def is_scope_authorized(self, decoded_token: str, scope: str) -> bool:
        ...
    
    @abstractmethod
    def get_username(self, decoded_token: str) -> Optional[str]:
        ...
    
    @abstractmethod
    def get_roles_for_user(self, user: User, role_assignment_resource_key: Optional[str]) -> List[Dict]:
        ...


class TokenServiceProtocol(SocaBaseProtocol):

    @abstractmethod
    def get_access_token_using_client_credentials(self, cached=True) -> AuthResult:
        ...

    @abstractmethod
    def decode_token(self, token: str, verify_exp: Optional[bool] = True) -> Dict:
        ...

    @abstractmethod
    def is_token_expired(self, token: str) -> bool:
        ...


class ApiInvokerProtocol(SocaBaseProtocol):

    @abstractmethod
    def get_token_service(self) -> Optional[TokenServiceProtocol]:
        ...

    @abstractmethod
    def get_api_authorization_service(self) -> Optional[APIAuthorizationServiceProtocol]:
        ...

    @abstractmethod
    def invoke(self, context: ApiInvocationContextProtocol):
        ...

    def get_request_logging_payload(self, context: ApiInvocationContextProtocol) -> Optional[Dict]:
        """
        implement any applicable redactions / exclusions for the request payload
        :param context: ApiInvocationContext
        :return: request payload
        """
        ...

    def get_response_logging_payload(self, context: ApiInvocationContextProtocol) -> Optional[Dict]:
        """
        implement any applicable redactions / exclusions for the response payload
        :param context: ApiInvocationContext
        :return: response payload
        """
        ...


class DistributedLockProtocol(SocaBaseProtocol):

    @abstractmethod
    def acquire(self, key: str):
        pass

    @abstractmethod
    def release(self, key: str):
        pass
