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
import json
import re

from ideasdk.protocols import AwsClientProviderProtocol, AWSUtilProtocol, SocaContextProtocol, PagingCallback
from ideasdk.launch_configurations import LaunchRoleHelper
from ideasdk.utils import Utils
from ideadatamodel import (
    exceptions, errorcodes, constants,
    SocaAmount,
    EC2InstanceType, AutoScalingGroup, CloudFormationStack, CloudFormationStackResources,
    EC2Instance, EC2SpotFleetRequestConfig, EC2SpotFleetInstance, EC2InstanceUnitPrice, AwsProjectBudget,
    SocaJob, SecurityGroup, Policy, AWSTag
)
from ideasdk.aws import EC2InstanceTypesDB

from typing import Dict, List, Optional, Tuple, Set, Callable, TypeVar
import botocore.exceptions
from threading import RLock
from ast import literal_eval
import time

T = TypeVar('T')

PAGE_SIZE = 20
INVALID_SG_CACHE_TTL_SECS = 60
INVALID_INSTANCE_PROFILE_CACHE_TTL_SECS = 60
INVALID_S3_BUCKET_HAS_ACCESS_TTL_SECS = 60
CLOUD_FORMATION_STACK_TTL_SECS = 60


class AWSUtil(AWSUtilProtocol):
    """
    AWS Utils for RES

    Instance Type Terms used in this implementation:

        > Instance Type: Name of the instance type
        > Instance Family: The part before . in the instance type.
        > Instance Class: A code identifying the class of instance type

        Below are a few examples:

        Instance Type       Instance Family         Instance Class
        -------------       ---------------         --------------
        m5ad.large          m5ad                    M
        vt1.3xlarge         vt1                     VT
        u-6tb1.112xlarge    u-6tb1                  HighMem
        inf1.6xlarge        inf1                    Inf

        See implementation of get_instance_type_class() for more details.

    Testing Notes:
        DO NOT UNIT TEST THIS CLASS WITHOUT CACHING AS IT WILL RESULT IN 1000s of EC2 API CALLS
        InstanceMonitor service should be up and running prior to testing.
    """

    def __init__(self, context: SocaContextProtocol, aws: AwsClientProviderProtocol = None):
        self._context = context
        self._logger = context.logger()
        self._ec2_instance_types_db = EC2InstanceTypesDB(context=self._context)
        self._cluster_config_lock = RLock()
        self._aws = aws

    def aws(self) -> AwsClientProviderProtocol:
        if self._aws is not None:
            return self._aws
        return self._context.aws()

    @staticmethod
    def is_valid_s3_bucket_arn(bucket_arn: str):
        bucket_arn_regex = re.compile(constants.S3_BUCKET_ARN_REGEX)
        if bucket_arn_regex.match(bucket_arn):
            return True
        else:
            return False

    @staticmethod
    def is_valid_iam_role_arn(iam_role_arn: str):
        iam_role_arn_regex = re.compile(constants.IAM_ROLE_ARN_REGEX)
        if iam_role_arn_regex.match(iam_role_arn):
            return True
        else:
            return False

    @staticmethod
    def is_valid_iam_role_name(iam_role_name: str):
        iam_role_name_regex = re.compile(constants.IAM_ROLE_NAME_REGEX)
        if iam_role_name_regex.match(iam_role_name):
            return True
        else:
            return False

    @staticmethod
    def get_bucket_name_from_bucket_arn(bucket_arn: str):
        bucket_arn_regex = re.compile(constants.S3_BUCKET_ARN_REGEX)
        match = bucket_arn_regex.match(bucket_arn)
        if match:
            return match.group(1)
        else:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message=constants.S3_BUCKET_ARN_ERROR_MESSAGE
            )

    @staticmethod
    def get_instance_type_class(instance_type: str) -> Tuple[str, bool]:
        """
        given an instance type, return it's instance class
        refer: https://aws.amazon.com/ec2/instance-types/

        implementation notes:
            > it's not really necessary to keep this mapping updated as just a basic check
                of startswith( 1st character of instance type) should do the job.
            > there are certain exceptions:
                - Trn: starts with trn and can conflict with (T)
                    since we check (Trn) instance before (T), this case will not occur.
                - Inf: starts with inf and can conflict with (I)
                    since we check (Inf) instance before (I), this case will not occur.
                - DL: starts with dl and can conflict with (D)
                    since we check (DL) instance before (D), this case will not occur.
                - HighMem: starts with u-
                    !! if AWS adds new instance type starting with u-, this implementation
                    needs to be revisited.
                - mac: starts with mac and can conflict with (M)
                    since we check mac instance before m instances, this case will not occur.
                - hpc: starts with h and can conflict with (H)
                    since we check (hpc) instance before (H), this case will not occur.

        :returns a tuple:
            > [0] = instance class (A, C, D.. )
            > [1] = True if standard, False if non-standard
        """
        family = instance_type.split('.')[0].lower()

        # accelerated computing
        if family.startswith(('p4de', 'p4d', 'p3dn', 'p3', 'p2', 'p')):
            return 'P', False
        elif family.startswith(('dl1', 'dl')):
            return 'DL', False  # todo - verify instance class in quota
        elif family.startswith(('inf1', 'inf')):
            return 'Inf', False
        elif family.startswith(('trn1', 'trn')):
            return 'Trn', False
        elif family.startswith(('g4dn', 'g4ad', 'g5', 'g5g', 'g3s', 'g3', 'g2', 'g')):
            return 'G', False
        elif family.startswith(('f1', 'f')):
            return 'F', False
        elif family.startswith(('vt1', 'vt')):
            return 'VT', False
        # storage optimized
        elif family.startswith(('i4i', 'i3', 'i3en', 'i')):  # standard
            return 'I', True
        elif family.startswith('lm4gn'):
            return 'lm4gn', True
        elif family.startswith('ls4gen'):
            return 'ls4gen', True
        elif family.startswith(('d2', 'd3', 'd3en', 'd')):  # standard
            return 'D', True
        elif family.startswith(('hpc6a', 'hpc')):
            return 'HPC', False
        elif family.startswith(('h1', 'h')):  # standard
            return 'H', False
        # memory optimized
        elif family.startswith(('r6a', 'r6g', 'r6i', 'r5a', 'r5b', 'r5d', 'r5dn', 'r5ad', 'r5n', 'r6', 'r5', 'r4', 'r')):  # standard
            return 'R', True
        elif family.startswith(('x2gd', 'x2idn', 'x2iedn', 'x2iezn', 'x1e', 'x1', 'x')):
            return 'X', False
        elif family.startswith('u-'):
            return 'HighMem', False
        elif family.startswith(('z1d', 'z')):  # standard
            return 'Z', True
        # compute optimized
        elif family.startswith(('c7g', 'c6g', 'c6gn', 'c6i', 'c5', 'c5a', 'c5n', 'c4', 'c')):  # standard
            return 'C', True
        # general purpose
        elif family.startswith(('mac1', 'mac2', 'mac')):
            return 'mac', False
        elif family.startswith(('t4g', 't3', 't3a', 't2', 't')):  # standard
            return 'T', True
        elif family.startswith(('m6g', 'm6gd', 'm6i', 'm6id', 'm6a', 'm5', 'm5a', 'm5d', 'm5ad', 'm5dn', 'm5n', 'm5zn', 'm4', 'm')):  # standard
            return 'M', True
        elif family.startswith(('a1', 'a')):  # standard
            return 'A', True

    def get_all_instance_types(self) -> Set[str]:
        return self._ec2_instance_types_db.all_instance_type_names()

    def get_instance_types_for_class(self, instance_class: str) -> List[str]:
        if instance_class == 'HighMem':
            token = 'u-'
        else:
            token = instance_class.lower()

        result = []
        all_instance_types = self.get_all_instance_types()
        for instance_type in all_instance_types:
            if instance_type.startswith(token):
                result.append(instance_type)

        return result

    def get_ec2_instance_type(self, instance_type: str) -> Optional[EC2InstanceType]:
        return self._ec2_instance_types_db.get(instance_type=instance_type)

    def is_instance_type_valid(self, instance_type: str) -> bool:
        try:
            self.get_ec2_instance_type(instance_type=instance_type)
            return True
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.INVALID_EC2_INSTANCE_TYPE:
                return False
            else:
                raise e

    def is_instance_type_efa_supported(self, instance_type: str) -> bool:
        ec2_instance_type = self.get_ec2_instance_type(instance_type=instance_type)
        return ec2_instance_type.network_info_efa_supported

    def s3_bucket_has_access(self, bucket_name: str) -> Dict:
        cache_key = f'aws.s3.bucket.{bucket_name}.has_access'
        result = self._context.cache().long_term().get(cache_key)
        if result is not None:
            return result
        try:
            self.aws().s3().get_bucket_acl(
                Bucket=bucket_name
            )
            result = {
                'success': True
            }
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                result = {
                    'success': False,
                    'error_code': 'AccessDenied'
                }
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                result = {
                    'success': False,
                    'error_code': 'NoSuchBucket'
                }
            else:
                raise e

        if result['success']:
            self._context.cache().long_term().set(key=cache_key, value=result)
        else:
            self._context.cache().long_term().set(key=cache_key, value=result,
                                                  ttl=INVALID_S3_BUCKET_HAS_ACCESS_TTL_SECS)

        return result

    def invoke_aws_listing(self, fn: Callable, result_cb: Callable[..., List[T]],
                           fn_kwargs: Dict = None,
                           max_results: int = 1000,
                           marker_based_paging=False, page_size_supported=True, **result_cb_kwargs) -> List[T]:
        """
        Generic method to invoke AWS paginated APIs

        :param fn: the AWS function to invoke
        :param result_cb: a callback that processes the listing result and returns a List[SocaClusterResource]
        :param fn_kwargs: Arguments to be passed to the function
        :param max_results: the total results that can be returned (not to be confused with page_size).
        :param marker_based_paging: specify if the AWS API uses marker based paging instead of token
        :param page_size_supported: indicates if MaxResults or MaxItems is supported in request.
        :return: list of SocaClusterResource
        """

        has_more_results = True
        next_token = None
        result = []
        page_size = 20

        while has_more_results:

            if fn_kwargs is None:
                fn_kwargs = {}

            if next_token:
                if marker_based_paging:
                    fn_kwargs['Marker'] = next_token
                    if page_size_supported:
                        fn_kwargs['MaxItems'] = page_size
                else:
                    fn_kwargs['NextToken'] = next_token
                    if page_size_supported:
                        fn_kwargs['MaxResults'] = page_size

            response = fn(**fn_kwargs)

            current_result = result_cb(response, **result_cb_kwargs)
            if current_result is not None:
                result += current_result

            if marker_based_paging:
                next_token = Utils.get_value_as_string('Marker')
            else:
                next_token = Utils.get_value_as_string('NextToken')

            if next_token is None:
                has_more_results = False

            if len(result) >= max_results:
                break

        return result

    def ec2_describe_instances(self, filters: list = None, page_size: int = PAGE_SIZE,
                               paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:
        token = True
        next_token = None

        if filters is None:
            filters = []

        result: Optional[List[Dict]] = None
        if paging_callback is None:
            result = []

        while token is True:

            instances = []

            if next_token:
                response = self.aws().ec2().describe_instances(
                    Filters=filters,
                    MaxResults=page_size,
                    NextToken=next_token,
                )
            else:
                response = self.aws().ec2().describe_instances(
                    Filters=filters,
                    MaxResults=page_size
                )

            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                token = False

            if 'Reservations' not in response:
                break

            for reservation in response['Reservations']:

                if 'Instances' not in reservation:
                    continue

                for instance in reservation['Instances']:
                    soca_custom_fields = {
                        'OwnerId': Utils.get_value_as_string('OwnerId', reservation),
                        'RequesterId': Utils.get_value_as_string('RequesterId', reservation),
                        'ReservationId': Utils.get_value_as_string('ReservationId', reservation)
                    }
                    instance['SocaCustomFields'] = soca_custom_fields
                    instances.append(EC2Instance(data=instance))

            if paging_callback is None:
                result += instances
            else:
                paging_callback(instances)

        return result

    def ec2_describe_compute_instances(self, instance_states: Optional[List[str]], page_size: int = PAGE_SIZE,
                                       paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:

        if instance_states is None or len(instance_states) == 0:
            instance_states = ['running']

        return self.ec2_describe_instances(
            filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': instance_states
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_NODE_TYPE}',
                    'Values': [constants.NODE_TYPE_COMPUTE]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_KEEP_FOREVER}',
                    'Values': ['true', 'false']
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_ENVIRONMENT_NAME}',
                    'Values': [self._context.cluster_name()]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_MODULE_ID}',
                    'Values': [str(self._context.module_id())]
                }
            ],
            page_size=page_size
        )

    def ec2_describe_dcv_instances(self, instance_states: Optional[List[str]], page_size: int = PAGE_SIZE,
                                   paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2Instance]]:

        if instance_states is None or len(instance_states) == 0:
            instance_states = ['running']

        return self.ec2_describe_instances(
            filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': instance_states
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_NODE_TYPE}',
                    'Values': [constants.NODE_TYPE_DCV_HOST]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_ENVIRONMENT_NAME}',
                    'Values': [self._context.cluster_name()]
                }
            ],
            page_size=page_size
        )

    def ec2_describe_spot_fleet_request(self, spot_fleet_request_id: str) -> Optional[EC2SpotFleetRequestConfig]:
        result = self.aws().ec2().describe_spot_fleet_requests(
            SpotFleetRequestIds=[spot_fleet_request_id]
        )
        configs = Utils.get_value_as_list('SpotFleetRequestConfigs', result)
        if configs is None or len(configs) == 0:
            return None
        return EC2SpotFleetRequestConfig(entry=configs[0])

    def ec2_modify_spot_fleet_request(self, spot_fleet_request_id: str, target_capacity: int):
        self.aws().ec2().modify_spot_fleet_request(
            SpotFleetRequestId=spot_fleet_request_id,
            TargetCapacity=target_capacity
        )

    def ec2_describe_spot_fleet_instances(self,
                                          spot_fleet_request_id: str, page_size: int = PAGE_SIZE,
                                          max_results: int = PAGE_SIZE,
                                          paging_callback: Optional[PagingCallback] = None) -> Optional[List[EC2SpotFleetInstance]]:

        token = True
        next_token = None

        result: Optional[List[EC2SpotFleetInstance]] = None
        if paging_callback is None:
            result = []

        while token is True:

            instances = []

            if next_token:
                response = self.aws().ec2().describe_spot_fleet_instances(
                    SpotFleetRequestId=spot_fleet_request_id,
                    MaxResults=page_size,
                    NextToken=next_token
                )
            else:
                response = self.aws().ec2().describe_spot_fleet_instances(
                    SpotFleetRequestId=spot_fleet_request_id,
                    MaxResults=page_size
                )

            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                token = False

            if 'ActiveInstances' not in response:
                break

            for instance in response['ActiveInstances']:
                instances.append(EC2SpotFleetInstance(**instance))

            if paging_callback is None:
                result += instances
            else:
                paging_callback(instances)

            if len(result) >= max_results:
                return result

        return result

    def ec2_terminate_instances(self, instance_ids: List[str]):
        self.aws().ec2().terminate_instances(
            InstanceIds=instance_ids
        )

    def ec2_describe_reserved_instances(self, instance_types: List[str]) -> Dict[str, int]:

        cache_key = f'aws.ec2.describe_reserved_instances.{":".join(instance_types)}.result'

        response = self._context.cache().short_term().get(key=cache_key)
        if response is not None:
            return response

        result = self.aws().ec2().describe_reserved_instances(
            Filters=[
                {
                    'Name': 'instance-type',
                    'Values': instance_types
                },
                {
                    'Name': 'state',
                    'Values': ['active']
                }
            ]
        )

        response = {}
        if 'ReservedInstances' in result:
            for reservation in result['ReservedInstances']:
                instance_type = Utils.get_value_as_string('InstanceType', reservation)
                instance_count = Utils.get_value_as_int('InstanceCount', reservation, default=0)
                if instance_type in instance_types:
                    response[instance_type] += instance_count
                else:
                    response[instance_type] = instance_count

        self._context.cache().short_term().set(key=cache_key, value=response)

        return response

    def cloudformation_describe_stack(self, stack_name: str) -> Optional[CloudFormationStack]:
        cache_key = f'aws.cloudformation.stack.{stack_name}'
        stack = self._context.cache().short_term().get(key=cache_key)
        if stack is not None:
            return stack

        try:
            result = self.aws().cloudformation().describe_stacks(
                StackName=stack_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                return None
            else:
                raise e

        stacks = Utils.get_value_as_list('Stacks', result)
        entry = Utils.get_first(stacks)
        if entry is None:
            return None

        stack = CloudFormationStack(entry=entry)

        # if stack_status is not CREATE_COMPLETE, do not cache
        if stack.stack_status != 'CREATE_COMPLETE':
            return stack

        self._context.cache().short_term().set(key=cache_key, value=stack, ttl=CLOUD_FORMATION_STACK_TTL_SECS)
        return stack

    def cloudformation_describe_stack_resources(self, stack_name: str) -> Optional[CloudFormationStackResources]:
        result = self.aws().cloudformation().describe_stack_resources(
            StackName=stack_name
        )
        return CloudFormationStackResources(entry=result)

    def cloudformation_delete_stack(self, stack_name: str):
        cache_key = f'aws.cloudformation.stack.{stack_name}'
        template_cache_key = f'aws.cloudformation.stack.template.{stack_name}'
        self.aws().cloudformation().delete_stack(
            StackName=stack_name
        )
        self._context.cache().short_term().delete(key=cache_key)
        self._context.cache().short_term().delete(key=template_cache_key)

    def cloudformation_get_template(self, stack_name: str) -> Optional[str]:
        cache_key = f'aws.cloudformation.stack.template.{stack_name}'
        template = self._context.cache().short_term().get(key=cache_key)
        if template is not None:
            return template
        try:
            result = self.aws().cloudformation().get_template(
                StackName=stack_name,
                TemplateStage='Original'
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                self._logger.warning(f'CloudFormation Template not found for StackName: {stack_name}')
                return None
            else:
                raise e
        template = Utils.get_value_as_string('TemplateBody', result)
        self._context.cache().short_term().set(key=cache_key, value=template, ttl=CLOUD_FORMATION_STACK_TTL_SECS)
        return template

    def autoscaling_update_auto_scaling_group(self, auto_scaling_group_name: str, desired_capacity: int,
                                              min_size: Optional[int] = None,
                                              max_size: Optional[int] = None):
        if min_size is None:
            min_size = desired_capacity

        if max_size is None:
            max_size = desired_capacity

        self.aws().autoscaling().update_auto_scaling_group(
            AutoScalingGroupName=auto_scaling_group_name,
            MinSize=min_size,
            MaxSize=max_size,
            DesiredCapacity=desired_capacity
        )

    def autoscaling_describe_auto_scaling_group(self, auto_scaling_group_name: str) -> Optional[AutoScalingGroup]:
        result = self.aws().autoscaling().describe_auto_scaling_groups(
            AutoScalingGroupNames=[auto_scaling_group_name]
        )
        groups = Utils.get_value_as_list('AutoScalingGroups', result)
        if groups is None or len(groups) == 0:
            return None
        return AutoScalingGroup(entry=groups[0])

    def autoscaling_detach_instances(self, auto_scaling_group_name: str, instance_ids: List[str],
                                     decrement_desired_capacity: bool = False):
        """
        detach the given instance ids from the auto-scaling group.
        optimizes the api calls and batches the requests if len(instance_ids) > 20 to prevent boto3 validation errors
        :param auto_scaling_group_name:
        :param instance_ids:
        :param decrement_desired_capacity:
        :return:
        """
        max_detach_limit = 20
        start = 0
        remaining = len(instance_ids)
        while remaining > 0:
            detach_instance_ids = instance_ids[start: start + max_detach_limit]
            self.aws().autoscaling().detach_instances(
                AutoScalingGroupName=auto_scaling_group_name,
                InstanceIds=detach_instance_ids,
                ShouldDecrementDesiredCapacity=decrement_desired_capacity
            )
            start += max_detach_limit
            remaining -= max_detach_limit
            if remaining > 0:
                # sleep to avoid being throttled
                time.sleep(0.5)

    def is_security_group_valid(self, security_group_id: str, filters: List[Dict] = None) -> bool:
        cache_key = f'aws.ec2.security_group.{security_group_id}.is_valid'

        # todo - documentation note: if cluster admin deletes a security group,
        #       this cache key needs to be deleted.
        # this can be optimized if we implement CloudWatch event that notify if a security group is deleted.

        is_valid = self._context.cache().long_term().get(key=cache_key)
        if is_valid is not None:
            return is_valid
        try:
            response = self.aws().ec2().describe_security_groups(
                GroupIds=[security_group_id],
                Filters=filters
            )
            is_valid = True
            if len(response['SecurityGroups']) == 0:
                is_valid = False
        except botocore.exceptions.ClientError as e:
            error_code = str(e.response['Error']['Code'])
            if error_code.startswith('InvalidGroup'):
                is_valid = False
            else:
                raise e

        if is_valid:
            self._context.cache().long_term().set(key=cache_key, value=is_valid)
        else:
            self._context.cache().long_term().set(key=cache_key, value=is_valid, ttl=INVALID_SG_CACHE_TTL_SECS)

        return is_valid

    def get_instance_profile_arn(self, instance_profile_name: str) -> Dict:

        cache_key = f'aws.ec2.instance_profile.{instance_profile_name}.arn'
        result = self._context.cache().long_term().get(key=cache_key)

        if result is not None:
            return result

        try:
            instance_profile_result = self.aws().iam().get_instance_profile(
                InstanceProfileName=instance_profile_name
            )
            result = {
                'success': True,
                'arn': instance_profile_result["InstanceProfile"]["Arn"]
            }
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                result = {
                    'success': False
                }
            else:
                raise e

        if result['success']:
            self._context.cache().long_term().set(key=cache_key, value=result)
        else:
            self._context.cache().long_term().set(key=cache_key, value=result,
                                                  ttl=INVALID_INSTANCE_PROFILE_CACHE_TTL_SECS)

        return result

    def get_purchased_ri_count(self, instance_type: str) -> int:
        cache_key = f'aws.ec2.purchased_ri.{instance_type}.count'
        result = self._context.cache().short_term().get(key=cache_key)
        if result is not None:
            return result[instance_type]

        result = self.ec2_describe_reserved_instances(
            instance_types=[instance_type]
        )
        if result is None or instance_type not in result:
            result = {
                instance_type: 0
            }
        self._context.cache().short_term().set(key=cache_key, value=result)
        return result[instance_type]

    def get_ec2_instance_type_unit_price(self, instance_type: str) -> EC2InstanceUnitPrice:

        cache_key = f'aws.pricing.instance-type.{instance_type}'

        pricing = self._context.cache().long_term().get(key=cache_key)
        if pricing is not None:
            return pricing

        # todo - move external / autodiscovery
        region_mapping = {
            "af-south-1": "AFS1-",
            "ap-east-1": "APE1-",
            "ap-northeast-1": "APN1-",
            "ap-northeast-2": "APN2-",
            "ap-northeast-3": "APN3-",
            "ap-south-1": "APS3-",
            "ap-southeast-1": "APS1-",
            "ap-southeast-2": "APS2-",
            "ap-southeast-3": "APS4-",
            "ca-central-1": "CAC1-",
            "eu-central-1": "EUC1-",
            "eu-north-1": "EUN1-",
            "eu-south-1": "EUS1-",
            "eu-west-1": "EUW1-",
            "eu-west-2": "EUW2-",
            "eu-west-3": "EUW3-",
            "me-central-1": "MEC1-",
            "me-south-1": "MES1-",
            "sa-east-1": "SAE1-",
            "us-east-1": "",
            "us-east-2": "USE2-",
            "us-gov-east-1": "UGE1-",
            "us-gov-west-1": "UGW1-",
            "us-west-1": "USW1-",
            "us-west-2": "USW2-"
        }

        region = self.aws().aws_region()
        try:
            response = self.aws().pricing().get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {
                        'Type': 'TERM_MATCH',
                        'Field': 'usageType',
                        'Value': f'{region_mapping[region]}BoxUsage:{instance_type}'
                    }
                ]
            )
        except Exception as err:
            # raise exceptions.soca_exception(
            #   error_code=errorcodes.GETPRODUCTS_FAILURE,
            #    message=f'GetProducts failure: {region}/{instance_type}: {err}'
            # )
            # todo - should this be a param to determine blocking behavior?
            # If we fail here - newly submitted jobs would fail for something like a pricing API failure.
            # todo - this also takes place in GovCloud as there is no pricing API endpoint _in_ GovCloud and we may not have commercial region credentials
            self._logger.warning(f'Failure trying to determine pricing for {region}/{instance_type}: {err}')
            pricing = EC2InstanceUnitPrice(
                ondemand=0.0,
                reserved=0.0
            )
            self._context.cache().long_term().set(key=cache_key, value=pricing)
            return pricing

        ondemand = 0.0
        reserved = 0.0
        for data in response['PriceList']:
            data = literal_eval(data)
            for k, v in data['terms'].items():
                if k == 'OnDemand':
                    for skus in v.keys():
                        for ratecode in v[skus]['priceDimensions'].keys():
                            instance_data = v[skus]['priceDimensions'][ratecode]
                            if f'on demand linux {instance_type} instance hour' in instance_data['description'].lower():
                                ondemand = float(instance_data['pricePerUnit']['USD'])
                else:
                    for skus in v.keys():
                        if v[skus]['termAttributes']['OfferingClass'] == 'standard' and v[skus]['termAttributes']['LeaseContractLength'] == '1yr' and v[skus]['termAttributes']['PurchaseOption'] == 'No Upfront':
                            for ratecode in v[skus]['priceDimensions'].keys():
                                instance_data = v[skus]['priceDimensions'][ratecode]
                                if 'Linux/UNIX (Amazon VPC)' in instance_data['description']:
                                    reserved = float(instance_data['pricePerUnit']['USD'])

        pricing = EC2InstanceUnitPrice(
            ondemand=ondemand,
            reserved=reserved
        )
        self._context.cache().long_term().set(key=cache_key, value=pricing)
        return pricing

    def budgets_get_budget(self, budget_name: str) -> Optional[AwsProjectBudget]:
        """
        given the name of the budget, find the budget limit and actual spend
        :param budget_name:
        :return: ProjectBudget with values. returns None if budget_name is not found.
        """

        aws_account_id = self._context.config().get_string('cluster.aws.account_id')
        cache_key = f'aws_budgets.{aws_account_id}.{budget_name}'
        budget = self._context.cache().short_term().get(key=cache_key)
        if budget is not None:
            return budget

        try:
            response = self.aws().budgets().describe_budget(
                AccountId=aws_account_id,
                BudgetName=budget_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                raise exceptions.soca_exception(
                    error_code=errorcodes.BUDGET_NOT_FOUND,
                    message=f'Budget not found: {budget_name}'
                )
            else:
                raise e

        response_budget = Utils.get_value_as_dict('Budget', response)

        actual_spend_result = None
        forecasted_spend_result = None

        budget_limit = Utils.get_value_as_dict('BudgetLimit', response_budget)
        budget_limit_amount = Utils.get_value_as_float('Amount', budget_limit)
        budget_limit_unit = Utils.get_value_as_string('Unit', budget_limit)
        budget_limit_result = SocaAmount(amount=budget_limit_amount, unit=budget_limit_unit)

        calculated_spend = Utils.get_value_as_dict('CalculatedSpend', response_budget)

        if calculated_spend is not None:
            actual_spend = Utils.get_value_as_dict('ActualSpend', calculated_spend)
            actual_spend_amount = Utils.get_value_as_float('Amount', actual_spend, default=0.0)
            actual_spend_unit = Utils.get_value_as_string('Unit', actual_spend)
            actual_spend_result = SocaAmount(amount=actual_spend_amount, unit=actual_spend_unit)

            forecasted_spend = Utils.get_value_as_dict('ForecastedSpend', calculated_spend)
            forecasted_spend_amount = Utils.get_value_as_float('Amount', forecasted_spend, default=0.0)
            forecasted_spend_unit = Utils.get_value_as_string('Unit', forecasted_spend)
            forecasted_spend_result = SocaAmount(amount=forecasted_spend_amount, unit=forecasted_spend_unit)

        budget = AwsProjectBudget(
            budget_name=budget_name,
            budget_limit=budget_limit_result,
            actual_spend=actual_spend_result,
            forecasted_spend=forecasted_spend_result
        )

        self._context.cache().short_term().set(key=cache_key, value=budget)

        return budget

    def get_soca_job_from_stack(self, stack_name: str) -> Optional[SocaJob]:
        template = self.cloudformation_get_template(stack_name=stack_name)
        if template is None:
            return None
        lines = template.splitlines()
        job_lines = []
        header_begin = -1
        header = -1
        header_end = -1
        for index, line in enumerate(lines):
            if not line.startswith('#'):
                continue
            if line.startswith('# ---'):
                if header >= 0:
                    header_end = index
                else:
                    header_begin = index
                continue
            if 'IDEA Job' in line:
                header = index
                continue

            if header_begin >= 0 and header > 0 and header_end > 0:
                if not line.startswith('#'):
                    continue
                if line.startswith('# ---'):
                    continue
                line = line.replace('# ', '')
                job_lines.append(line)

        if len(job_lines) == 0:
            return None
        job_json = "".join(job_lines)
        job = Utils.from_json(job_json)
        return SocaJob(**job)

    def handle_aws_exception(self, e):
        missing_permissions = False
        if isinstance(e, botocore.exceptions.ClientError):
            if e.response['Error']['Code'] in ('UnauthorizedOperation',
                                               'AuthFailure',
                                               'InvalidClientTokenId',
                                               'ExpiredToken'):
                missing_permissions = True
        elif isinstance(e, botocore.exceptions.ProfileNotFound):
            missing_permissions = True

        if missing_permissions:
            raise exceptions.soca_exception(
                error_code=errorcodes.AWS_MISSING_PERMISSIONS,
                message=f'AWS credentials are expired or do not have access to perform '
                        f'required operations on AWS Partition or Region.',
                ref=e
            )
        else:
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'An unhandled exception occurred: {e}',
                ref=e
            )

    def dynamodb_check_table_exists(self, table_name: str, wait: bool = False) -> bool:
        try:
            while True:
                describe_table_result = self.aws().dynamodb().describe_table(TableName=table_name)

                if not wait:
                    return True

                table = describe_table_result['Table']
                created = table['TableStatus'] == 'ACTIVE'

                if created:
                    return True

                time.sleep(2)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:
                raise e

    def get_default_dynamodb_tags(self):
        default_tags = {
            constants.IDEA_TAG_ENVIRONMENT_NAME: self._context.cluster_name(),
            constants.IDEA_TAG_MODULE_NAME: self._context.module_name(),
            constants.IDEA_TAG_MODULE_ID: self._context.module_id(),
            constants.IDEA_TAG_BACKUP_PLAN: f'{self._context.cluster_name()}-{constants.MODULE_CLUSTER}'
        }
        custom_tags = self._context.config().get_list('global-settings.custom_tags', [])
        custom_tags_dict = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
        return {
            **custom_tags_dict,
            **default_tags
        }

    def dynamodb_create_table(self, create_table_request: Dict, wait: bool = False, ttl: bool = False, ttl_attribute_name: str = None) -> bool:
        """
        create a new dynamodb table

        optionally specify if ttl should be enabled for the table.
        does not support disabling ttl. call update_time_to_live() api separately to disable ttl on a table.
        does not support updating ttl for existing tables.  call update_time_to_live() api separately to enable ttl on an existing table.

        :param create_table_request:
        :param wait: wait for table creation and status to become active
        :param ttl: specify if time to live should be enabled on a table
        :param ttl_attribute_name: the name of the attribute for enabling ttl. required when `ttl` = True
        :return: True is table did not exist and was created. Returns False if table already exists
        """

        table_name = create_table_request['TableName']

        exists = self.dynamodb_check_table_exists(table_name, wait)
        if exists:
            return False

        if ttl:
            if Utils.is_empty(ttl_attribute_name):
                raise exceptions.invalid_params('ttl_attribute_name is required when ttl = True')

        self._logger.info(f'creating dynamodb table: {table_name} ...')

        # custom tags + mandatory tags for table
        tags = Utils.get_value_as_list('Tags', create_table_request, [])
        tag_updates = self.get_default_dynamodb_tags()

        updated_tags = []
        for tag in tags:
            key = tag['Key']
            if key in tag_updates:
                continue
            updated_tags.append(tag)
        for tag_key, tag_value in tag_updates.items():
            updated_tags.append({
                'Key': tag_key,
                'Value': tag_value
            })
        create_table_request['Tags'] = updated_tags

        dynamodb_kms_key_id = self._context.config().get_string('cluster.dynamodb.kms_key_id')
        if dynamodb_kms_key_id is not None:
            create_table_request['SSESpecification'] = {
                    'Enabled': True,
                    'SSEType': 'KMS',
                    'KMSMasterKeyId': dynamodb_kms_key_id
                    }

        self.aws().dynamodb().create_table(**create_table_request)

        if wait or ttl:
            self.dynamodb_check_table_exists(table_name, True)

        if ttl:
            self.aws().dynamodb().update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute_name
                }
            )

        return True

    def dynamodb_import_table(self, import_table_request: Dict, wait: bool = False):
        """
        Import table data from S3 to DynamoDB table
        :param import_table_request:
        """

        table_creation_parameters = import_table_request.get('TableCreationParameters')
        if not table_creation_parameters:
            raise exceptions.invalid_params("import_table_request must include 'TableCreationParameters'")
        table_name = table_creation_parameters.get("TableName")
        if not table_name:
            raise exceptions.invalid_params("import_table_request must include 'TableCreationParameters.TableName'")
        s3_bucket_source = import_table_request.get('S3BucketSource')
        if not s3_bucket_source:
            raise exceptions.invalid_params("import_table_request must include 'S3BucketSource'")
        s3_bucket_name = s3_bucket_source.get('S3Bucket')
        s3_key_prefix = s3_bucket_source.get('S3KeyPrefix')
        if not s3_bucket_name or not s3_key_prefix:
            raise exceptions.invalid_params("import_table_request must include 'S3BucketSource.S3Bucket' and 'S3BucketSource.S3KeyPrefix'. One or both were not provided")
        dynamodb_kms_key_id = self._context.config().get_string('cluster.dynamodb.kms_key_id')
        if dynamodb_kms_key_id is not None:
            import_table_request['TableCreationParameters']['SSESpecification'] = {
                'Enabled': True,
                'SSEType': 'KMS',
                'KMSMasterKeyId': dynamodb_kms_key_id
                }
        self._logger.info(f'importing table {table_name} from S3 bucket {s3_bucket_name} and path {s3_key_prefix} to dynamodb table: {table_name} ...')
        # Response for the query takes about 5 seconds. The response ensures that the table creation process has started.
        res = self.aws().dynamodb().import_table(**import_table_request)
        return res

    def dynamodb_check_import_completed_successfully(self, import_arn: str) -> bool:
        while True:
            describe_import_result = self.aws().dynamodb().describe_import(ImportArn=import_arn)

            result = describe_import_result['ImportTableDescription']
            if result['ImportStatus'] == 'COMPLETED':
                return True
            elif result['ImportStatus'] == 'CANCELLED':
                self._logger.error(f'Import attempt {import_arn} was CANCELLED')
                return False
            elif result['ImportStatus'] == 'FAILED':
                self._logger.error(f"Import attempt {import_arn} FAILED with code: {result['FailureCode']} and message: {result['FailureMessage']}")
                return False

            time.sleep(10)

    def dynamodb_delete_table(self, table_name: str, wait: bool = True) -> bool:
        """
        Deletes a DynamoDB table if exists. Most likely used for deletion of temp tables created during ApplySnapshot process

        :param table_name: Name of the DDB table that should be deleted
        :param wait: wait for table creation and status to become active
        """
        if wait:
            try:
                self.dynamodb_check_table_exists(table_name, wait)
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    return True
        self.aws().dynamodb().delete_table(TableName=table_name)
        return True

    def create_s3_presigned_url(self, key: str, expires_in=3600) -> str:
        return self.aws().s3().generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self._context.config().get_string('cluster.cluster_s3_bucket', required=True),
                'Key': key
            },
            ExpiresIn=expires_in
        )

    def create_vdi_host_role(self, role_name: str, permissions_boundary: Optional[str]) -> bool:
        region = self.aws().aws_region()
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ssm.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        arguments = {
            "Path":f'/{LaunchRoleHelper.get_vdi_role_path(cluster_name=self._context.cluster_name(), region=region)}/',
            "Description": f'{role_name} used for VDI instance',
            "RoleName": role_name,
            "AssumeRolePolicyDocument": json.dumps(assume_role_policy_document),
        }
        if permissions_boundary:
            self.aws().iam().create_role(
                **arguments,
                PermissionsBoundary=permissions_boundary
            )
        else:
            self.aws().iam().create_role(**arguments)
        return True

    def delete_vdi_host_role(self, role_name) -> bool:
        try:
            self.aws().iam().delete_role(
                RoleName=role_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                return True
            raise e
        return True

    def attach_role_policy(self, role_name: str, policy_arn: str) -> bool:
        try:
            self.aws().iam().attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                raise exceptions.invalid_params('Policy arn provided does not exist')
            raise e
        return True

    def detach_role_policy(self, role_name: str, policy_arn: str) -> bool:
        try:
            self.aws().iam().detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                return True
            raise e
        return True

    def create_vdi_instance_profile(self, instance_profile_name: str) -> bool:
        region = self.aws().aws_region()
        self.aws().iam().create_instance_profile(
            InstanceProfileName=instance_profile_name,
            Path=f'/{LaunchRoleHelper.get_vdi_instance_profile_path(cluster_name=self._context.cluster_name(), region=region)}/'
        )
        return True

    def delete_vdi_instance_profile(self, instance_profile_name: str) -> bool:

        try:
            self.aws().iam().delete_instance_profile(
                InstanceProfileName=instance_profile_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                return True
            raise e
        return True

    def add_role_to_instance_profile(self, role_name: str, instance_profile_name: str) -> bool:
        try:
            self.aws().iam().add_role_to_instance_profile(
                InstanceProfileName=instance_profile_name,
                RoleName=role_name
            )
        except botocore.exceptions.ClientError as e:
            return False
        return True

    def is_policy_valid(self, policy_arn: str) -> bool:
        try:
            self.aws().iam().get_policy(PolicyArn=policy_arn)
        except botocore.exceptions.ClientError as e:
            return False
        return True

    def does_vdi_role_exist(self, role_name: str) -> bool:
        try:
            response = self.aws().iam().get_role(RoleName=role_name)
            role = response['Role']
            region = self.aws().aws_region()
            if role['Path'] != f'/{LaunchRoleHelper.get_vdi_role_path(cluster_name=self._context.cluster_name(), region=region)}/':
                return False
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                return False
            elif e.response['Error']['Code'] == 'AccessDenied':
                return False
            raise e

    def list_available_security_groups(self, vpc_id: str) -> List[SecurityGroup]:
        try:
            def result_cb(result) -> List[SecurityGroup]:
                results = []
                listing = Utils.get_value_as_list('SecurityGroups', result, [])
                for entry in listing:
                    group_id = entry['GroupId']
                    group_name = entry['GroupName']
                    results.append(SecurityGroup(
                        group_id=group_id,
                        group_name=group_name
                    ))
                return results
            # Retrieve security groups that have been tagged for RES
            filter_tags = [
                {
                    'Name': 'tag:' + constants.VDI_RESOURCE_TAG_KEY,
                    'Values': [constants.VDI_SECURITY_GROUP_RESOURCE_TAG]
                },
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                }
            ]
            security_groups = self.invoke_aws_listing(
                fn=self.aws().ec2().describe_security_groups,
                result_cb=result_cb,
                fn_kwargs={
                    "Filters": filter_tags
                }
            )
            return security_groups
        except Exception as e:
            self.handle_aws_exception(e)

    def list_available_host_policies(self) -> List[Policy]:
        try:
            def result_cb(result) -> List[Policy]:
                results = [Policy(policy_arn=policy['Arn'], policy_name=policy['PolicyName'])
                           for policy in result.get('Policies', [])
                           if self.is_policy_valid(policy['Arn'])]
                return results

            # Will currently only grab customer managed policies
            policies = self.invoke_aws_listing(
                fn=self.aws().iam().list_policies,
                result_cb=result_cb,
                fn_kwargs={
                    'Scope': 'Local'
                }
            )
            return policies
        except Exception as e:
            self.handle_aws_exception(e)

    def is_security_group_available(self, security_group_id: str, vpc_id: str) -> bool:
        # Retrieve security groups that have been tagged for RES
        filter_tags = [
            {
                'Name': 'tag:' + constants.VDI_RESOURCE_TAG_KEY,
                'Values': [constants.VDI_SECURITY_GROUP_RESOURCE_TAG]
            },
            {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }
        ]
        return self.is_security_group_valid(security_group_id, filter_tags)

    def does_iam_role_exist(self, role_arn: str, filter_tags: List[AWSTag] = None) -> bool:
        try:
            match = re.compile(constants.IAM_ROLE_NAME_CAPTURE_GROUP_REGEX).search(role_arn)
            if match:
                role_name = match.group(1)
            else:
                return False
            response = self.aws().iam().get_role(RoleName=role_name)
            role = response['Role']
            tags = {tag['Key']: tag['Value'] for tag in role.get('Tags', [])}
            if filter_tags:
                for tag in filter_tags:
                    key = tag.Key
                    value = tag.Value
                    if tags.get(key) != value:
                        return False
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                return False
            elif e.response['Error']['Code'] == 'AccessDenied':
                return False
            raise e
