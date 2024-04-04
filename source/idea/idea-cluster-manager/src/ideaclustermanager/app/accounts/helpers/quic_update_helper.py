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
from enum import Enum

from ideadatamodel import constants
from ideasdk.context import SocaContext

TCP = 'TCP'
QUIC = 'QUIC'
TCP_PROTOCOL = 'TCP'
QUIC_PROTOCOL = 'TCP_UDP'
LISTENER_PORT = 443
TARGET_GROUP_PORT = 8443


class UpdateQuicResults(Enum):
    SUCCESS = "SUCCESS"
    ROLLBACK_COMPLETE = "ROLLBACK_COMPLETE"
    ERROR = "ERROR"


class QuicUpdateHelper:

    def __init__(self, context: SocaContext):
        self.context = context
        self.cluster_name = self.context._options.cluster_name
        self.logger = context.logger('update-quic')

    def update_quic_config(self, enabled: bool) -> UpdateQuicResults:
        if enabled:
            return self.update_quic_config_steps(QUIC_PROTOCOL, QUIC)
        else:
            return self.update_quic_config_steps(TCP_PROTOCOL, TCP)

    def update_quic_config_steps(self, protocol: str, config: str) -> UpdateQuicResults:
        self.logger.info(f"Enabling {config}")
        try:
            external_nlb_arn = self.context.config().get_string('virtual-desktop-controller.external_nlb_arn',
                                                                required=True)
            current_target_group = \
            self.context.aws().elbv2().describe_target_groups(LoadBalancerArn=external_nlb_arn).get('TargetGroups',
                                                                                                    [None])[0]
            current_listener = \
            self.context.aws().elbv2().describe_listeners(LoadBalancerArn=external_nlb_arn).get('Listeners', [None])[0]
            # Delete Listener
            self.context.aws().elbv2().delete_listener(ListenerArn=current_listener['ListenerArn'])
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.logger.error(f"Aborting enabling {config}")
            return UpdateQuicResults.ROLLBACK_COMPLETE
        # Delete Target Group
        try:
            self.context.aws().elbv2().delete_target_group(TargetGroupArn=current_target_group['TargetGroupArn'])
        except Exception as e:
            self.logger.error(f"Delete Target Group Error: {e}")
            self.logger.info(f"Aborting enabling {config}")
            return self.rollback(config, current_target_group, external_nlb_arn)
        # Create new target group
        try:
            new_target_group_arn = self.create_target_group(current_target_group['TargetGroupName'], protocol,
                                                            current_target_group['VpcId'])
        except Exception as e:
            self.logger.error(f"Create New Target Group Error: {e}")
            self.logger.error(f"Aborting enabling {config}")
            return self.rollback(config, current_target_group, external_nlb_arn)
        # Create listener to use new target group
        try:
            new_listener_arn = self.create_listener(external_nlb_arn, protocol, new_target_group_arn)
        except Exception as e:
            self.logger.error(f"Create Load Balancer Listener Error: {e}")
            self.logger.info(f"Aborting enabling {config}")
            return self.rollback(config, current_target_group, external_nlb_arn, new_target_group_arn)
        try:
            self.update_egress(config)
        except Exception as e:
            self.logger.error(f"Updating egress Error: {e}")
            self.logger.info(f"Aborting enabling {config}")
            return self.rollback(config, current_target_group, external_nlb_arn, new_target_group_arn, new_listener_arn)
        self.update_quic_flag(config)
        self.logger.info(f"{config} Enabled")
        return UpdateQuicResults.SUCCESS

    def rollback(self, config: str, current_target_group: dict, external_nlb_arn: str,
                 new_target_group_arn: str = None, new_listener_arn: str = None) -> UpdateQuicResults:
        if config == QUIC:
            return self.execute_rollback_steps(TCP_PROTOCOL, TCP, current_target_group, external_nlb_arn,
                                               new_target_group_arn, new_listener_arn)
        else:
            return self.execute_rollback_steps(QUIC_PROTOCOL, QUIC, current_target_group, external_nlb_arn,
                                               new_target_group_arn, new_listener_arn)

    def execute_rollback_steps(self, protocol: str, config: str, current_target_group: dict, external_nlb_arn: str,
                               new_target_group_arn: str = None, new_listener_arn: str = None) -> UpdateQuicResults:
        self.logger.info("Starting Rollback")
        # Delete newly created listener if created
        if new_listener_arn is not None:
            try:
                self.context.aws().elbv2().delete_listener(ListenerArn=new_listener_arn)
            except Exception as e:
                self.logger.error(f"Deleting Newly Created Listener Error: {e}")
                self.logger.error(f"Error while rolling back to {config}")
                return UpdateQuicResults.ERROR
        # Delete newly created target group if created
        if new_target_group_arn is not None:
            try:
                self.context.aws().elbv2().delete_target_group(TargetGroupArn=new_target_group_arn)
            except Exception as e:
                self.logger.error(f"Deleting Newly Created Target Group Error: {e}")
                self.logger.error(f"Error while rolling back to {config}")
                return UpdateQuicResults.ERROR
        # Create new target group using current
        try:
            roll_back_target_group_arn = self.create_target_group(current_target_group['TargetGroupName'], protocol,
                                                                  current_target_group['VpcId'])
        except Exception as e:
            self.logger.error(f"Create New Target Group Error: {e}")
            self.logger.error(f"Error while rolling back to {config}")
            return UpdateQuicResults.ERROR
        # Create listener using current
        try:
            self.create_listener(external_nlb_arn, protocol, roll_back_target_group_arn)
        except Exception as e:
            self.logger.error(f"Modify Load Balancer Listener Error: {e}")
            self.logger.info(f"Error while rolling back to {config}")
            return UpdateQuicResults.ERROR
        self.logger.info("Rollback Complete")
        return UpdateQuicResults.ROLLBACK_COMPLETE

    def update_egress(self, config: str):
        gateway_security_group_id = self.context.config().get_string(
            'virtual-desktop-controller.gateway_security_group_id', required=True)
        if config == QUIC:
            self.context.aws().ec2().authorize_security_group_egress(
                GroupId=gateway_security_group_id,
                IpPermissions=[
                    {
                        'FromPort': 8443,
                        'IpProtocol': 'udp',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "Allow UDP egress for port 8443"
                            },
                        ],
                        'ToPort': 8443,
                    }
                ]
            )
        else:
            self.context.aws().ec2().revoke_security_group_egress(
                GroupId=gateway_security_group_id,
                IpPermissions=[
                    {
                        'FromPort': 8443,
                        'IpProtocol': 'udp',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "Allow UDP egress for port 8443"
                            },
                        ],
                        'ToPort': 8443,
                    }
                ]
            )

    def update_quic_flag(self, config: str):
        if config == QUIC:
            value = True
        else:
            value = False
        module_id = self.context.config().get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)
        self.context.config().db.set_config_entry(f'{module_id}.dcv_session.quic_support', value)
        self.context.config().put(f'{module_id}.dcv_session.quic_support', value)

    def create_listener(self, external_nlb_arn: str, protocol: str, target_group_arn: str) -> str:
        return self.context.aws().elbv2().create_listener(
            LoadBalancerArn=external_nlb_arn,
            Protocol=protocol,
            Port=LISTENER_PORT,
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': target_group_arn
                }
            ]
        ).get('Listeners', [None])[0]['ListenerArn']

    def create_target_group(self, target_group_name: str, protocol: str, vpc_id: str):
        target_group_arn = self.context.aws().elbv2().create_target_group(
            Name=target_group_name,
            Protocol=protocol,
            Port=TARGET_GROUP_PORT,
            VpcId=vpc_id,
            HealthCheckProtocol='TCP',
            HealthCheckPort="8989",
            TargetType='instance',
            Tags=[
                {
                    'Key': 'res:EnvironmentName',
                    'Value': self.cluster_name
                },
                {
                    'Key': 'res:ModuleId',
                    'Value': 'vdc'
                },
                {
                    'Key': 'res:ModuleName',
                    'Value': 'virtual-desktop-controller'
                },
                {
                    'Key': 'res:ModuleVersion',
                    'Value': self.context.module_version()
                }
            ]
        ).get('TargetGroups', [None])[0]['TargetGroupArn']
        try:
            vdc_gateway_instance_id = self.context.aws().ec2().describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [f'{self.cluster_name}-vdc-gateway']
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    }
                ]
            ).get('Reservations', [None])[0].get('Instances', [None])[0]['InstanceId']
        except Exception as e:
            self.logger.error(f"Error while describing instances: {e}")
            self.logger.error("No gateway instance found")
            raise e
        self.context.aws().elbv2().register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[
                {
                    'Id': vdc_gateway_instance_id
                }
            ]
        )
        return target_group_arn
