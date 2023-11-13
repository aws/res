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

import ideavirtualdesktopcontroller
from ideasdk.context import ArnBuilder
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler


class DCVBrokerUserdataExecutionCompleteEventHandler(BaseVirtualDesktopControllerEventHandler):
    SCALING_POLICY_TYPE_READ_CAPACITY_UTILIZATION = 'DynamoDBReadCapacityUtilization'
    SCALING_POLICY_TYPE_WRITE_CAPACITY_UTILIZATION = 'DynamoDBWriteCapacityUtilization'
    SERVICE_NAMESPACE_DYNAMO_DB = 'dynamodb'

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'dcv-broker-boot-complete-handler')
        self.application_autoscaling_client = self.context.aws().application_autoscaling()
        self.dynamodb_client = self.context.aws().dynamodb()
        self.arn_builder = ArnBuilder(self.context.config())

    def _add_tags_to_table(self, message_id: str, table_name: str):
        self.log_info(message_id=message_id, message=f'Tagging {table_name}...')
        default_tags = self.context.aws_util().get_default_dynamodb_tags()
        tags = []
        for tag_key, tag_value in default_tags.items():
            tags.append({
                'Key': tag_key,
                'Value': tag_value
            })

        self.dynamodb_client.tag_resource(
            ResourceArn=self.arn_builder.get_ddb_table_arn(
                table_name_suffix='.'.join(table_name.split('.')[1:])  # removing cluster-name from the table name because the utility appends cluster name internally
            ),
            Tags=tags
        )

    def _create_scaling_policies_for_ddb_table_if_required(self, message_id: str, table_name: str):
        self.log_debug(message_id=message_id, message=f'Trying to create scaling policies for {table_name}...')
        if Utils.is_empty(table_name):
            return

        resource_id = f'table/{table_name}'
        read_capacity_resource_policy_exists = False
        write_capacity_resource_policy_exists = False

        response = self.application_autoscaling_client.describe_scaling_policies(
            ServiceNamespace=self.SERVICE_NAMESPACE_DYNAMO_DB,
            ResourceId=resource_id
        )

        existing_scaling_policies = Utils.get_value_as_list('ScalingPolicies', response, [])
        for existing_scaling_policy in existing_scaling_policies:
            target_tracking_policy_config = Utils.get_value_as_dict('TargetTrackingScalingPolicyConfiguration', existing_scaling_policy, {})
            predefined_metric_spec = Utils.get_value_as_dict('PredefinedMetricSpecification', target_tracking_policy_config, {})
            predefined_metric_type = Utils.get_value_as_string('PredefinedMetricType', predefined_metric_spec, None)
            if predefined_metric_type == self.SCALING_POLICY_TYPE_READ_CAPACITY_UTILIZATION:
                self.log_debug(message_id=message_id, message=f'Read scaling policy for {table_name} already exists...')
                read_capacity_resource_policy_exists = True
            elif predefined_metric_type == self.SCALING_POLICY_TYPE_WRITE_CAPACITY_UTILIZATION:
                self.log_debug(message_id=message_id, message=f'Write scaling policy for {table_name} already exists...')
                write_capacity_resource_policy_exists = True
            else:
                # some other policy exists, that we are not tracking
                self.log_debug(message_id=message_id, message=f'Some other scaling policy for {table_name} already exists...')
                pass

        if write_capacity_resource_policy_exists and read_capacity_resource_policy_exists:
            # both policies already exist. Nothing to do here.
            return

        if not read_capacity_resource_policy_exists:
            self.log_info(message_id=message_id, message=f'Creating read scaling policy for {table_name}...')
            _ = self.application_autoscaling_client.register_scalable_target(
                ServiceNamespace=self.SERVICE_NAMESPACE_DYNAMO_DB,
                ResourceId=resource_id,
                ScalableDimension='dynamodb:table:ReadCapacityUnits',
                MaxCapacity=self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.read_capacity.max_units', required=True),
                MinCapacity=self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.read_capacity.min_units', default=5)
            )
            _ = self.application_autoscaling_client.put_scaling_policy(
                ServiceNamespace=self.SERVICE_NAMESPACE_DYNAMO_DB,
                ResourceId=resource_id,
                PolicyName=f'{self.context.cluster_name()}-{self.context.module_id()}-{table_name}-read-scaling-policy',
                ScalableDimension='dynamodb:table:ReadCapacityUnits',
                PolicyType='TargetTrackingScaling',
                TargetTrackingScalingPolicyConfiguration={
                    'TargetValue': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.read_capacity.target_utilization', required=True),
                    'ScaleInCooldown': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.read_capacity.scale_in_cooldown', required=True),
                    'ScaleOutCooldown': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.read_capacity.scale_out_cooldown', required=True),
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': self.SCALING_POLICY_TYPE_READ_CAPACITY_UTILIZATION
                    }
                }
            )

        if not write_capacity_resource_policy_exists:
            self.log_info(message_id=message_id, message=f'Creating write scaling policy for {table_name}...')
            _ = self.application_autoscaling_client.register_scalable_target(
                ServiceNamespace=self.SERVICE_NAMESPACE_DYNAMO_DB,
                ResourceId=resource_id,
                ScalableDimension='dynamodb:table:WriteCapacityUnits',
                MaxCapacity=self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.write_capacity.max_units', required=True),
                MinCapacity=self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.write_capacity.min_units', default=5)
            )
            _ = self.application_autoscaling_client.put_scaling_policy(
                ServiceNamespace=self.SERVICE_NAMESPACE_DYNAMO_DB,
                ResourceId=resource_id,
                PolicyName=f'{self.context.cluster_name()}-{self.context.module_id()}-{table_name}-write-scaling-policy',
                ScalableDimension='dynamodb:table:WriteCapacityUnits',
                PolicyType='TargetTrackingScaling',
                TargetTrackingScalingPolicyConfiguration={
                    'TargetValue': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.write_capacity.target_utilization', required=True),
                    'ScaleInCooldown': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.write_capacity.scale_in_cooldown', required=True),
                    'ScaleOutCooldown': self.context.config().get_int('virtual-desktop-controller.dcv_broker.dynamodb_table.write_capacity.scale_out_cooldown', required=True),
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': self.SCALING_POLICY_TYPE_WRITE_CAPACITY_UTILIZATION
                    }
                }
            )

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_dcv_broker_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        table_names = self.dcv_broker_client_utils.get_broker_dynamodb_table_names()
        autoscaling_enabled = self.context.config().get_bool('virtual-desktop-controller.dcv_broker.dynamodb_table.autoscaling.enabled', default=True)
        for table_name in table_names:
            if autoscaling_enabled:
                self._create_scaling_policies_for_ddb_table_if_required(message_id, table_name)
            self._add_tags_to_table(message_id, table_name)
