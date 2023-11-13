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

from ideadatamodel.model_utils import ModelUtils
from ideadatamodel import constants

from typing import Dict, Any, Optional, List
import arrow


class EC2Instance:
    """
    Soca wrapper class over EC2 Describe Instances result entry

    See below link for more information on the response structure:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    """

    def __init__(self, data: Dict[str, Any]):
        self._instance = data

    def __eq__(self, other: 'EC2Instance'):
        return self.instance_id == other.instance_id

    def __dict__(self):
        return self._instance

    def __str__(self):
        s = f'Host: {self.private_dns_name}, ' \
            f'InstanceId: {self.instance_id}'
        if self.is_idea_compute_node():
            s += f', ComputeStack: {self.soca_compute_stack}'
        return s

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.instance_id)

    def instance_data(self) -> Optional[Dict[str, Any]]:
        return self._instance

    @property
    def reservation_id(self) -> Optional[str]:
        soca_custom_fields = ModelUtils.get_value_as_dict('SocaCustomFields', self.instance_data())
        return ModelUtils.get_value_as_string('ReservationId', soca_custom_fields)

    @property
    def requester_id(self) -> Optional[str]:
        soca_custom_fields = ModelUtils.get_value_as_dict('SocaCustomFields', self.instance_data())
        return ModelUtils.get_value_as_string('RequesterId', soca_custom_fields)

    @property
    def owner_id(self) -> Optional[str]:
        soca_custom_fields = ModelUtils.get_value_as_dict('SocaCustomFields', self.instance_data())
        return ModelUtils.get_value_as_string('OwnerId', soca_custom_fields)

    @property
    def ami_launch_index(self) -> Optional[int]:
        return ModelUtils.get_value_as_int('AmiLaunchIndex', self.instance_data())

    @property
    def image_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('ImageId', self.instance_data())

    @property
    def instance_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('InstanceId', self.instance_data())

    @property
    def instance_type(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('InstanceType', self.instance_data())

    @property
    def kernel_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('KernelId', self.instance_data())

    @property
    def key_name(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('KeyName', self.instance_data())

    @property
    def launch_time(self) -> Optional[arrow.Arrow]:
        if 'LaunchTime' not in self._instance:
            return None
        return arrow.get(self._instance.get('LaunchTime'))

    @property
    def monitoring_state(self) -> Optional[str]:
        monitoring = ModelUtils.get_value_as_dict('Monitoring', self.instance_data())
        return ModelUtils.get_value_as_string('State', monitoring)

    @property
    def placement_availability_zone(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('AvailabilityZone', placement)

    @property
    def placement_affinity(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('Affinity', placement)

    @property
    def placement_group_name(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('GroupName', placement)

    @property
    def placement_partition_number(self) -> Optional[int]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_int('PartitionNumber', placement)

    @property
    def placement_host_id(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('HostId', placement)

    @property
    def placement_tenancy(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('Tenancy', placement)

    @property
    def placement_spread_domain(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('SpreadDomain', placement)

    @property
    def placement_host_resource_group_arn(self) -> Optional[str]:
        placement = ModelUtils.get_value_as_dict('Placement', self.instance_data())
        return ModelUtils.get_value_as_string('HostResourceGroupArn', placement)

    @property
    def platform(self) -> Optional[str]:
        """
        The value is Windows for Windows instances; otherwise blank.
        """
        return ModelUtils.get_value_as_string('Platform', self.instance_data())

    @property
    def private_dns_name(self) -> Optional[str]:
        fqdn = self.private_dns_name_fqdn
        if fqdn is None:
            return None
        return fqdn.split('.')[0]

    @property
    def private_dns_name_fqdn(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('PrivateDnsName', self.instance_data())

    @property
    def private_ip_address(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('PrivateIpAddress', self.instance_data())

    @property
    def product_codes(self) -> Optional[List[Dict]]:
        return ModelUtils.get_value_as_list('ProductCodes', self.instance_data())

    @property
    def public_dns_name(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('PublicDnsName', self.instance_data())

    @property
    def public_ip_address(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('PublicIpAddress', self.instance_data())

    @property
    def ramdisk_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('RamdiskId', self.instance_data())

    @property
    def state(self) -> Optional[str]:
        state = ModelUtils.get_value_as_dict('State', self.instance_data())
        return ModelUtils.get_value_as_string('Name', state)

    @property
    def state_code(self) -> Optional[int]:
        """
        :return: state code int value
            0 : pending
            16 : running
            32 : shutting-down
            48 : terminated
            64 : stopping
            80 : stopped
            You can ignore the high byte value by zeroing out all of the bits above 2^8 or 256 in decimal.
        """
        state = ModelUtils.get_value_as_dict('State', self.instance_data())
        return ModelUtils.get_value_as_int('Code', state)

    @property
    def is_running(self) -> bool:
        return self.state == 'running'

    @property
    def is_pending(self) -> bool:
        return self.state == 'pending'

    @property
    def is_stopped(self) -> bool:
        return self.state in ('stopping', 'stopped')

    @property
    def is_terminated(self) -> bool:
        return self.state in ('shutting-down', 'terminated')

    @property
    def state_transition_reason(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('StateTransitionReason', self.instance_data())

    @property
    def subnet_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('SubnetId', self.instance_data())

    @property
    def vpc_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('VpcId', self.instance_data())

    @property
    def architecture(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('Architecture', self.instance_data())

    @property
    def block_device_mappings(self) -> Optional[List[Dict]]:
        return ModelUtils.get_value_as_list('BlockDeviceMappings', self.instance_data())

    @property
    def client_token(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('ClientToken', self.instance_data())

    @property
    def ebs_optimized(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('EbsOptimized', self.instance_data())

    @property
    def ena_support(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('EnaSupport', self.instance_data())

    @property
    def hypervisor(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('Hypervisor', self.instance_data())

    @property
    def iam_instance_profile_arn(self) -> Optional[str]:
        instance_profile = ModelUtils.get_value_as_dict('IamInstanceProfile', self.instance_data())
        return ModelUtils.get_value_as_string('Arn', instance_profile)

    @property
    def iam_instance_profile_id(self) -> Optional[str]:
        instance_profile = ModelUtils.get_value_as_dict('IamInstanceProfile', self.instance_data())
        return ModelUtils.get_value_as_string('Id', instance_profile)

    @property
    def instance_lifecycle(self) -> Optional[str]:
        """
        Indicates whether this is a Spot Instance or a Scheduled Instance.
        """
        return ModelUtils.get_value_as_string('InstanceLifecycle', self.instance_data())

    @property
    def elastic_gpu_associations(self) -> Optional[List[Dict]]:
        # todo - expand this further after testing GPU based use cases
        return ModelUtils.get_value_as_list('ElasticGpuAssociations', self.instance_data())

    @property
    def elastic_inference_accelerator_associations(self) -> Optional[List[Dict]]:
        # todo - expand this further after testing inference accelerator based use cases
        return ModelUtils.get_value_as_list('ElasticInferenceAcceleratorAssociations', self.instance_data())

    @property
    def network_interfaces(self) -> Optional[List[Dict]]:
        # todo - this needs to be revisited for container based workloads using ECS/EKS
        #  as there is a potential for 100s of network interfaces attached to a single instance
        return ModelUtils.get_value_as_list('NetworkInterfaces', self.instance_data())

    @property
    def outpost_arn(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('OutpostArn', self.instance_data())

    @property
    def root_device_name(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('RootDeviceName', self.instance_data())

    @property
    def root_device_type(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('RootDeviceType', self.instance_data())

    @property
    def security_groups(self) -> Optional[List[Dict]]:
        return ModelUtils.get_value_as_list('SecurityGroups', self.instance_data())

    @property
    def source_dest_check(self) -> Optional[bool]:
        return ModelUtils.get_value_as_bool('SourceDestCheck', self.instance_data())

    @property
    def spot_instance_request_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('SpotInstanceRequestId', self.instance_data())

    @property
    def sriov_net_support(self) -> Optional[str]:
        """
        Specifies whether enhanced networking with the Intel 82599 Virtual Function interface is enabled.
        """
        return ModelUtils.get_value_as_string('SriovNetSupport', self.instance_data())

    @property
    def state_reason_code(self) -> Optional[str]:
        state_reason = ModelUtils.get_value_as_dict('StateReason', self.instance_data())
        return ModelUtils.get_value_as_string('Code', state_reason)

    @property
    def state_reason_message(self) -> Optional[str]:
        """
        The message for the state change.

        Server.InsufficientInstanceCapacity
            There was insufficient capacity available to satisfy the launch request.
        Server.InternalError
            An internal error caused the instance to terminate during launch.
        Server.ScheduledStop
            The instance was stopped due to a scheduled retirement.
        Server.SpotInstanceShutdown
            The instance was stopped because the number of Spot requests with a maximum price equal to or higher than
            the Spot price exceeded available capacity or because of an increase in the Spot price.
        Server.SpotInstanceTermination
            The instance was terminated because the number of Spot requests with a maximum price equal to or higher
            than the Spot price exceeded available capacity or because of an increase in the Spot price.
        Client.InstanceInitiatedShutdown
            The instance was shut down using the shutdown -h command from the instance.
        Client.InstanceTerminated
            The instance was terminated or rebooted during AMI creation.
        Client.InternalError
            A client error caused the instance to terminate during launch.
        Client.InvalidSnapshot.NotFound
            The specified snapshot was not found.
        Client.UserInitiatedHibernate
            Hibernation was initiated on the instance.
        Client.UserInitiatedShutdown
            The instance was shut down using the Amazon EC2 API.
        Client.VolumeLimitExceeded
            The limit on the number of EBS volumes or total storage was exceeded. Decrease usage or request an
            increase in your account limits.

        :return: message for code listed above
        """
        state_reason = ModelUtils.get_value_as_dict('StateReason', self.instance_data())
        return ModelUtils.get_value_as_string('Message', state_reason)

    @property
    def tags(self) -> Optional[Dict[str, str]]:
        tags = ModelUtils.get_value_as_list('Tags', self.instance_data())
        if tags is None:
            return None
        result = {}
        for tag in tags:
            key = ModelUtils.get_value_as_string('Key', tag)
            value = ModelUtils.get_value_as_string('Value', tag)
            result[key] = value
        return result

    @property
    def virtualization_type(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('VirtualizationType', self.instance_data())

    @property
    def cpu_options_core_count(self) -> Optional[int]:
        cpu_options = ModelUtils.get_value_as_dict('CpuOptions', self.instance_data())
        return ModelUtils.get_value_as_int('CoreCount', cpu_options)

    @property
    def cpu_options_threads_per_core(self) -> Optional[int]:
        cpu_options = ModelUtils.get_value_as_dict('CpuOptions', self.instance_data())
        return ModelUtils.get_value_as_int('ThreadsPerCore', cpu_options)

    @property
    def capacity_reservation_id(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('CapacityReservationId', self.instance_data())

    @property
    def capacity_reservation_preference(self) -> Optional[str]:
        """
        open
            The instance can run in any open Capacity Reservation that has matching attributes
            (instance type, platform, Availability Zone).
        none
            The instance avoids running in a Capacity Reservation even if one is available.
            The instance runs in On-Demand capacity.
        :return: preference value
        """
        spec = ModelUtils.get_value_as_dict('CapacityReservationSpecification', self.instance_data())
        return ModelUtils.get_value_as_string('CapacityReservationPreference', spec)

    @property
    def capacity_reservation_target_id(self) -> Optional[str]:
        spec = ModelUtils.get_value_as_dict('CapacityReservationSpecification', self.instance_data())
        target = ModelUtils.get_value_as_dict('CapacityReservationTarget', spec)
        return ModelUtils.get_value_as_string('CapacityReservationId', target)

    @property
    def capacity_reservation_target_resource_group_arn(self) -> Optional[str]:
        spec = ModelUtils.get_value_as_dict('CapacityReservationSpecification', self.instance_data())
        target = ModelUtils.get_value_as_dict('CapacityReservationTarget', spec)
        return ModelUtils.get_value_as_string('CapacityReservationResourceGroupArn', target)

    @property
    def hibernation_options_configured(self) -> Optional[bool]:
        options = ModelUtils.get_value_as_dict('HibernationOptions', self.instance_data())
        return ModelUtils.get_value_as_bool('Configured', options)

    @property
    def licenses(self) -> Optional[List[Dict]]:
        return ModelUtils.get_value_as_list('Licenses', self.instance_data())

    @property
    def metadata_options_state(self) -> Optional[str]:
        options = ModelUtils.get_value_as_dict('MetadataOptions', self.instance_data())
        return ModelUtils.get_value_as_string('State', options)

    @property
    def metadata_options_http_tokens(self) -> Optional[str]:
        options = ModelUtils.get_value_as_dict('MetadataOptions', self.instance_data())
        return ModelUtils.get_value_as_string('HttpTokens', options)

    @property
    def metadata_options_http_put_response_hop_limit(self) -> Optional[int]:
        options = ModelUtils.get_value_as_dict('MetadataOptions', self.instance_data())
        return ModelUtils.get_value_as_int('HttpPutResponseHopLimit', options)

    @property
    def metadata_options_http_endpoint(self) -> Optional[str]:
        """
        Indicates whether the HTTP metadata endpoint on your instances is enabled or disabled.
        """
        options = ModelUtils.get_value_as_dict('MetadataOptions', self.instance_data())
        return ModelUtils.get_value_as_string('HttpEndpoint', options)

    @property
    def metadata_options_http_protocol_ipv6(self) -> Optional[str]:
        options = ModelUtils.get_value_as_dict('MetadataOptions', self.instance_data())
        return ModelUtils.get_value_as_string('HttpProtocolIpv6', options)

    @property
    def enclave_options_enabled(self) -> Optional[bool]:
        options = ModelUtils.get_value_as_dict('EnclaveOptions', self.instance_data())
        return ModelUtils.get_value_as_bool('Enabled', options)

    @property
    def boot_mode(self) -> Optional[str]:
        # see https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ami-boot.html for more info
        return ModelUtils.get_value_as_string('BootMode', self.instance_data())

    @property
    def platform_details(self) -> Optional[str]:
        """
        The platform details associated with the billing code of the AMI. For example, Red Hat Enterprise Linux.
        see: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/billing-info-fields.html for more info
        """
        return ModelUtils.get_value_as_string('PlatformDetails', self.instance_data())

    @property
    def usage_operation(self) -> Optional[str]:
        """
        The operation of the Amazon EC2 instance and the billing code that is associated with the AMI.
        For example, RunInstances:0010.
        Usage operation corresponds to the lineitem/Operation column on your AWS Cost and
        Usage Report (CUR) and in the AWS Price List API.
        see: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/billing-info-fields.html for more info
        """
        return ModelUtils.get_value_as_string('UsageOperation', self.instance_data())

    @property
    def usage_operation_update_time(self) -> Optional[arrow.Arrow]:
        if 'UsageOperationUpdateTime' not in self._instance:
            return None
        return arrow.get(self._instance.get('UsageOperationUpdateTime'))

    def as_dict(self) -> Dict[str, Any]:
        # todo - deep copy? let's verify use-cases and then implement.
        return self._instance

    def get_tag(self, key: str) -> Optional[str]:
        tags = ModelUtils.get_value_as_list('Tags', self.instance_data())
        if tags is None:
            return None
        for tag in tags:
            tag_key = ModelUtils.get_value_as_string('Key', tag)
            if tag_key == key:
                return ModelUtils.get_value_as_string('Value', tag)
        return None

    @property
    def aws_ec2spot_fleet_request_id(self):
        return self.get_tag(constants.AWS_TAG_EC2SPOT_FLEET_REQUEST_ID)

    @property
    def aws_autoscaling_group_name(self):
        return self.get_tag(constants.AWS_TAG_AUTOSCALING_GROUP_NAME)

    @property
    def aws_cloudformation_stack_name(self):
        return self.get_tag(constants.AWS_TAG_CFN_STACK_NAME)

    @property
    def aws_cloudformation_stack_id(self):
        return self.get_tag(constants.AWS_TAG_CFN_STACK_ID)

    @property
    def aws_cloudformation_logical_id(self):
        return self.get_tag(constants.AWS_TAG_CFN_LOGICAL_ID)

    # begin soca custom properties and operations

    @property
    def soca_cluster_name(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_ENVIRONMENT_NAME)

    @property
    def soca_node_type(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_NODE_TYPE)

    @property
    def idea_module_id(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_MODULE_ID)

    @property
    def soca_job_id(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_ID)

    @property
    def soca_job_group(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_GROUP)

    @property
    def soca_job_name(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_NAME)

    @property
    def soca_job_owner(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_OWNER)

    @property
    def soca_job_queue(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_QUEUE)

    @property
    def soca_queue_type(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_QUEUE_TYPE)

    @property
    def soca_job_project(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_PROJECT)

    @property
    def soca_keep_forever(self) -> bool:
        value = self.get_tag(constants.IDEA_TAG_KEEP_FOREVER)
        return ModelUtils.get_as_bool(value, default=False)

    @property
    def soca_terminate_when_idle(self) -> int:
        value = self.get_tag(constants.IDEA_TAG_TERMINATE_WHEN_IDLE)
        return ModelUtils.get_as_int(value, default=0)

    @property
    def is_soca_ephemeral_capacity(self) -> bool:
        keep_forever = self.soca_keep_forever
        if keep_forever:
            return False
        terminate_when_idle = self.soca_terminate_when_idle
        if terminate_when_idle > 0:
            return False
        return True

    @property
    def soca_fsx(self) -> Optional[bool]:
        value = self.get_tag(constants.IDEA_TAG_FSX)
        return ModelUtils.get_as_bool(value)

    @property
    def soca_compute_stack(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_COMPUTE_STACK)

    @property
    def soca_created_from(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_CREATED_FROM)

    @property
    def soca_created_on(self) -> Optional[arrow.Arrow]:
        value = self.get_tag(constants.IDEA_TAG_CREATED_ON)
        if value is None:
            return None
        return arrow.get(value)

    @property
    def soca_backup_plan(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_BACKUP_PLAN)

    @property
    def soca_scaling_mode(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_SCALING_MODE)

    @property
    def soca_capacity_type(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_CAPACITY_TYPE)

    def is_idea_compute_node(self) -> bool:
        node_type = self.soca_node_type
        if node_type is None:
            return False
        return node_type == constants.NODE_TYPE_COMPUTE

    def is_soca_dcv_node(self) -> bool:
        node_type = self.soca_node_type
        if node_type is None:
            return False
        return node_type == constants.NODE_TYPE_DCV_HOST

    @property
    def node_type(self) -> str:
        if self.is_idea_compute_node():
            return constants.NODE_TYPE_COMPUTE
        elif self.is_soca_dcv_node():
            return constants.NODE_TYPE_DCV_HOST
        else:
            return constants.NODE_TYPE_UNKNOWN

    def is_valid_idea_compute_node(self) -> bool:
        if not self.is_idea_compute_node():
            return False

        job_id = self.soca_job_id
        if job_id is None:
            return False

        return True

    def is_current_cluster(self, cluster_name: str) -> bool:
        instance_cluster_name = self.soca_cluster_name
        if instance_cluster_name is None:
            return False
        if instance_cluster_name is None:
            return False
        return instance_cluster_name == cluster_name
