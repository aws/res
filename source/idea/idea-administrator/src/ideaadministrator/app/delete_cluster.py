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

from ideasdk.context import SocaCliContext, SocaContextOptions
from ideasdk.config.cluster_config_db import ClusterConfigDB
from ideasdk.utils import Utils
from ideadatamodel import constants, exceptions, errorcodes, EC2Instance, SocaMemory, SocaMemoryUnit

from typing import Optional, List, Mapping
from prettytable import PrettyTable
import time
import botocore.exceptions

class DeleteCluster:

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str, delete_bootstrap: bool, delete_databases: bool, delete_backups: bool, delete_cloudwatch_logs: bool, delete_all: bool, force: bool):
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.delete_bootstrap = delete_bootstrap
        self.delete_databases = delete_databases
        self.delete_backups = delete_backups
        self.delete_cloudwatch_logs = delete_cloudwatch_logs
        self.delete_all = delete_all
        self.force = force
        self.delete_failed_attempt = 0
        self.delete_failed_max_attempts = 3

        self.context = SocaCliContext(
            options=SocaContextOptions(
                aws_region=aws_region,
                aws_profile=aws_profile,
                enable_aws_client_provider=True,
                enable_aws_util=True
            )
        )

        try:
            self.cluster_config_db = ClusterConfigDB(
                cluster_name=cluster_name,
                aws_region=aws_region,
                aws_profile=aws_profile
            )
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.CLUSTER_CONFIG_NOT_INITIALIZED:
                self.cluster_config_db: Optional[ClusterConfigDB] = None
            else:
                raise e

        if self.cluster_config_db is not None:
            self.cluster_modules = self.cluster_config_db.get_cluster_modules()
        else:
            self.cluster_modules = []

        self.app_modules = []
        for cluster_module in self.cluster_modules:
            module_type = Utils.get_value_as_string('type', cluster_module, None)
            if module_type == 'app':
                self.app_modules.append(cluster_module)

        self.ec2_instances = []
        self.termination_protected_ec2_instances = []

        # all stacks that belong to the cluster, but not the actual cluster stack
        self.cloud_formation_stacks = []
        # cluster stack. there will most likely be only one stack, but the modular data structures do support multiple stack for clusters.
        self.cluster_stacks = []
        # Identity Provider stacks - requires disable of the UserPool protection
        self.identity_provider_stacks = []

        self.dynamodb_tables = []

        self.cloudwatch_logs = []

    def get_bootstrap_stack_name(self) -> str:
        return f'{self.cluster_name}-bootstrap'

    def find_ec2_instances(self):
        self.context.info('Searching for EC2 instances to be terminated ...')
        ec2_instances_to_delete = []
        termination_protected_instances = []
        ec2_instances = self.context.aws_util().ec2_describe_instances(
            filters=[
                {
                    'Name': f'tag:{constants.IDEA_TAG_ENVIRONMENT_NAME}',
                    'Values': [self.cluster_name]
                }
            ]
        )
        for ec2_instance in ec2_instances:
            if ec2_instance.state == 'terminated':
                continue

            if ec2_instance.get_tag(constants.BI_TAG_DEPLOYMENT) == "true":
                continue

            # check termination protection instances
            describe_instance_attribute_result = self.context.aws().ec2().describe_instance_attribute(
                Attribute='disableApiTermination',
                InstanceId=ec2_instance.instance_id
            )
            disable_api_termination = Utils.get_value_as_dict('DisableApiTermination', describe_instance_attribute_result)
            disable_api_termination_enabled = Utils.get_value_as_bool('Value', disable_api_termination, False)
            if disable_api_termination_enabled:
                termination_protected_instances.append(ec2_instance)
            time.sleep(0.1)  # 10 tps - might need to be adjusted in-future. allowed 100 TPS - https://docs.aws.amazon.com/AWSEC2/latest/APIReference/throttling.html

            # app and infra node type instances will be terminated by their respective cloudformation stacks
            # we are primarily interested in the instances launched without CloudFormation stack
            node_type = ec2_instance.soca_node_type
            if node_type in (constants.NODE_TYPE_APP, constants.NODE_TYPE_INFRA):
                continue
            ec2_instances_to_delete.append(ec2_instance)

        self.termination_protected_ec2_instances = termination_protected_instances
        self.ec2_instances = ec2_instances_to_delete

    @staticmethod
    def print_ec2_instances(ec2_instances: List[EC2Instance]):
        instance_table = PrettyTable(['Name', 'Instance Id', 'Private IP', 'Instance Type', 'Status'])
        instance_table.align = 'l'
        for ec2_instance in ec2_instances:
            instance_table.add_row([
                ec2_instance.get_tag('Name'),
                ec2_instance.instance_id,
                ec2_instance.private_ip_address,
                ec2_instance.instance_type,
                ec2_instance.state
            ])
        print(instance_table)

    def delete_ec2_instances(self):
        if len(self.termination_protected_ec2_instances) > 0:
            for ec2_instance in self.termination_protected_ec2_instances:
                self.context.info(f'disabling termination protection for EC2 instance: {ec2_instance.instance_id} ...')
                self.context.aws().ec2().modify_instance_attribute(
                    InstanceId=ec2_instance.instance_id,
                    DisableApiTermination={
                        'Value': False
                    }
                )
                self.context.success(f'termination protection disabled for EC2 instance: {ec2_instance.instance_id}')
                time.sleep(1)

        if len(self.ec2_instances) > 0:
            for ec2_instance in self.ec2_instances:
                self.context.info(f'terminating EC2 instance: {ec2_instance.instance_id}')
                self.context.aws().ec2().terminate_instances(
                    InstanceIds=[ec2_instance.instance_id]
                )
                self.context.success(f'terminated EC2 instance: {ec2_instance.instance_id}')
                time.sleep(1)

    def _get_app_instance(self, module_id: str) -> Optional[EC2Instance]:
        describe_instances_result = self.context.aws().ec2().describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['pending', 'stopped', 'running']
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_ENVIRONMENT_NAME}',
                    'Values': [self.cluster_name]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_MODULE_ID}',
                    'Values': [module_id]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_NODE_TYPE}',
                    'Values': ['app']
                }
            ]
        )

        reservations = Utils.get_value_as_list('Reservations', describe_instances_result, [])
        for reservation in reservations:
            instances = Utils.get_value_as_list('Instances', reservation)
            for instance in instances:
                ec2_instance = EC2Instance(instance)
                if ec2_instance.state == 'running':
                    return ec2_instance
        return None

    def invoke_app_app_module_clean_up(self):
        instance_ids = []
        for module in self.app_modules:
            module_id = Utils.get_value_as_string('module_id', module, None)
            if Utils.is_empty(module_id):
                continue

            app_instance = self._get_app_instance(module_id)
            if Utils.is_empty(app_instance):
                continue

            print(f'executing app-module-clean-up commands for app: {module_id}')
            instance_ids.append(app_instance.instance_id)

        command_to_execute = 'sudo resctl app-module-clean-up'
        if self.delete_databases:
            command_to_execute = f'{command_to_execute} --delete-databases'

        send_command_result = self.context.aws().ssm().send_command(
            InstanceIds=instance_ids,
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': [command_to_execute]
            }
        )

        command_id = send_command_result['Command']['CommandId']
        while True:
            list_command_invocations_result = self.context.aws().ssm().list_command_invocations(
                CommandId=command_id,
                Details=False
            )
            command_invocations = list_command_invocations_result['CommandInvocations']

            completed_count = 0
            failed_count = 0

            for command_invocation in command_invocations:
                status = command_invocation['Status']

                if status in ('Success', 'TimedOut', 'Cancelled', 'Failed'):
                    completed_count += 1

                if status in ('TimedOut', 'Cancelled', 'Failed'):
                    failed_count += 1

            if completed_count == len(command_invocations):
                break

            time.sleep(10)

    def find_cloud_formation_stacks(self):
        self.context.info(f'Searching for CloudFormation stacks to be terminated (matching {constants.IDEA_TAG_ENVIRONMENT_NAME} of {self.cluster_name})...')
        stacks_to_delete = []
        cluster_stacks = []
        identity_provider_stacks = []
        paginator = self.context.aws().cloudformation().get_paginator('list_stacks')
        page_iterator = paginator.paginate()
        # TODO: Use S3 select instead of looping on all the stacks for more efficient tag based querying 
        for page in page_iterator:
            for stacks in page.get('StackSummaries', []):
                stack_name = stacks.get('StackName')

                if not stack_name:
                    continue
                
                if not stack_name.strip().startswith(self.cluster_name):
                    continue
                
                stack_id = stacks.get('StackId')
                stack = self.describe_cloud_formation_stack(stack_id)
                
                if stack['StackStatus'] == 'DELETE_COMPLETE':
                    continue

                tags = stack.get('Tags', {})
                tag_value = None
                for tag in tags:
                    if tag['Key'] == constants.IDEA_TAG_ENVIRONMENT_NAME:
                        tag_value = tag['Value']
                        break

                if not tag_value or tag_value != self.cluster_name:
                    continue

                if self.is_bootstrap_stack(stack_name):
                    continue

                if self.is_batteries_included_stack(stack):
                    continue
                
                if self.is_cluster_stack(stack_name):
                    cluster_stacks.append(stack)
                elif self.is_identity_provider_stack(stack_name):
                    identity_provider_stacks.append(stack)
                else:
                    stacks_to_delete.append(stack)
                
                # sleep for a while to ensure we don't flood describe_stack() API
                time.sleep(0.5)
        self.cloud_formation_stacks = stacks_to_delete
        self.cluster_stacks = cluster_stacks
        self.identity_provider_stacks = identity_provider_stacks

    def print_cloud_formation_stacks(self):
        stacks_table = PrettyTable(['Stack Name', 'Status', 'Termination Protection'])
        stacks_table.align = 'l'
        stacks = self.cloud_formation_stacks + self.cluster_stacks
        for stack in stacks:
            stacks_table.add_row([
                Utils.get_value_as_string('StackName', stack),
                Utils.get_value_as_string('StackStatus', stack),
                Utils.get_value_as_bool('EnableTerminationProtection', stack, False)
            ])

        if len(stacks) > 0:
            print(stacks_table)
        print(f'{len(stacks)} stacks will be terminated.')

    def describe_cloud_formation_stack(self, stack_name: str):
        describe_stack_result = self.context.aws().cloudformation().describe_stacks(
            StackName=stack_name
        )
        stacks = Utils.get_value_as_list('Stacks', describe_stack_result)
        return stacks[0]

    def delete_cloud_formation_stack(self, stack_name: str):

        try:
            stack = self.describe_cloud_formation_stack(stack_name)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                return
            else:
                raise e

        enable_termination_protection = Utils.get_value_as_bool('EnableTerminationProtection', stack, False)
        if not self.force and enable_termination_protection:
            confirm = self.context.prompt(f'Termination protection is enabled for stack: {stack_name}. Disable and terminate?')
            if not confirm:
                self.context.error('Abort cluster deletion')
                raise SystemExit

        if enable_termination_protection:
            print(f'disabling termination protection for stack: {stack_name}')
            self.context.aws().cloudformation().update_termination_protection(
                EnableTerminationProtection=False,
                StackName=stack_name
            )

        print(f'terminating CloudFormation stack: {stack_name}')
        self.context.aws().cloudformation().delete_stack(
            StackName=stack_name
        )

    def delete_dynamo_table(self, table_name: str):
        try:
            print(f'deleting table: {table_name} ...')
            self.context.aws().dynamodb().delete_table(TableName=table_name)
            self.context.success(f'deleted dynamodb table: {table_name}')
        except botocore.exceptions.BotoCoreError as e:
            raise e

    def is_bootstrap_stack(self, stack_name: str) -> bool:
        return stack_name == self.get_bootstrap_stack_name()

    def is_batteries_included_stack(self, stack: Mapping) -> bool:
        stack_tags = Utils.get_value_as_list("Tags", stack)
        for tag in stack_tags:
            tag_dict = Utils.get_as_dict(tag, default={})
            if tag_dict["Key"] == constants.BI_TAG_DEPLOYMENT and tag_dict["Value"] == "true":
                return True
        return False

    def is_cluster_stack(self, stack_name: str) -> bool:
        for module in self.cluster_modules:
            module_name = module['name']
            if module_name == constants.MODULE_CLUSTER:
                cluster_stack_name = module['stack_name']
                if cluster_stack_name == stack_name:
                    return True
        if stack_name == f'{self.cluster_name}-cluster':
            return True
        return False

    def is_identity_provider_stack(self, stack_name: str) -> bool:
        for module in self.cluster_modules:
            module_name = module['name']
            if module_name == constants.MODULE_IDENTITY_PROVIDER:
                cluster_stack_name = module['stack_name']
                if cluster_stack_name == stack_name:
                    return True
        if stack_name == f'{self.cluster_name}-identity-provider':
            return True
        return False

    def try_delete_vpc_lambda_enis(self):
        # fix to address scenario where deleting lambda function in VPC takes a very long time
        # and in-turn causes cluster deletion to either fail
        describe_network_interfaces_result = self.context.aws().ec2().describe_network_interfaces(
            Filters=[
                {
                    'Name': 'description',
                    'Values': [
                        f'AWS Lambda VPC ENI-{self.cluster_name}-*'
                    ]
                },
                {
                    'Name': 'status',
                    'Values': [
                        'available'
                    ]
                }
            ]
        )
        network_interfaces = Utils.get_value_as_list('NetworkInterfaces', describe_network_interfaces_result, [])
        if len(network_interfaces) > 0:
            print('found VPC lambda network interfaces for the cluster in "available" state. deleting ...')
            for network_interface in network_interfaces:
                network_interface_id = network_interface['NetworkInterfaceId']
                description = network_interface['Description']
                print(f'deleting VPC Lambda ENI - NetworkInterfaceId: {network_interface_id}, Description: {description}')
                self.context.aws().ec2().delete_network_interface(
                    NetworkInterfaceId=network_interface_id
                )

    def detach_vpc_from_lambda_functions(self):
        # List all functions with a VPC configuration
        response = self.context.aws().lambda_().list_functions()
        vpc_functions = []
        # Filter functions based on tags
        for func in response['Functions']:
            if 'VpcConfig' in func:
                function_arn = func['FunctionArn']
                try:
                    tags = self.context.aws().lambda_().list_tags(Resource=function_arn)['Tags']
                    if tags.get(constants.IDEA_TAG_ENVIRONMENT_NAME) == self.cluster_name:
                        vpc_functions.append(func)
                except Exception as e:
                    print(f"Error retrieving tags for function {function_arn}: {e}")

        # Handle pagination if there are more functions
        while 'NextMarker' in response:
            response = self.context.aws().lambda_().list_functions(Marker=response['NextMarker'])
            for func in response['Functions']:
                if 'VpcConfig' in func:
                    function_arn = func['FunctionArn']
                    try:
                        tags = self.context.aws().lambda_().list_tags(Resource=function_arn)['Tags']
                        if tags.get(constants.IDEA_TAG_ENVIRONMENT_NAME) == self.cluster_name:
                            vpc_functions.append(func)
                    except Exception as e:
                        print(f"Error retrieving tags for function {function_arn}: {e}")

        # Remove the VPC configuration from each function
        for function in vpc_functions:
            function_name = function['FunctionName']
            print(f"Removing VPC configuration from function: {function_name}")
            
            try:
                self.context.aws().lambda_().update_function_configuration(
                    FunctionName=function_name,
                    VpcConfig={
                        'SubnetIds': [],
                        'SecurityGroupIds': []
                    }
                )
                print(f"VPC configuration removed from function: {function_name}")
            except Exception as e:
                print(f"Error removing VPC configuration from function {function_name}: {e}")
            

    def check_stack_deletion_status(self, stack_names: List[str]) -> bool:
        delete_failed = 0
        stacks_pending = list(stack_names)

        while len(stacks_pending) > 0:

            stacks_deleted = []
            for stack_name in stacks_pending:
                try:
                    describe_stack_result = self.context.aws().cloudformation().describe_stacks(
                        StackName=stack_name
                    )
                    stacks = Utils.get_value_as_list('Stacks', describe_stack_result)
                    stack = stacks[0]
                    stack_status = Utils.get_value_as_string('StackStatus', stack)

                    if stack_status == 'DELETE_COMPLETE':
                        self.context.success(f'stack: {stack_name}, status: {stack_status}')
                        stacks_deleted.append(stack_name)
                    elif stack_status == 'DELETE_FAILED':
                        if self.delete_failed_attempt < self.delete_failed_max_attempts:
                            self.context.warning(f'stack: {stack_name}, status: {stack_status}, submitting a new delete_cloud_formation_stack request. [Loop {self.delete_failed_attempt}/{self.delete_failed_max_attempts}]')
                            self.delete_cloud_formation_stack(stack_name)
                            self.delete_failed_attempt += 1
                        else:
                            self.context.error(f'stack: {stack_name}, status: {stack_status}')
                            stacks_deleted.append(stack_name)
                            delete_failed += 1
                    else:
                        print(f'stack: {stack_name}, status: {stack_status}')

                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        self.context.success(f'stack: {stack_name}, status: DELETE_COMPLETE')
                        stacks_deleted.append(stack_name)
                    else:
                        raise e

            for stack_name in stacks_deleted:
                stacks_pending.remove(stack_name)

            if len(stacks_pending) > 0:
                num_stacks_pending = len(stacks_pending)
                if num_stacks_pending == 1:
                    print(f'waiting for 1 stack to be deleted: {stacks_pending} ...')
                else:
                    print(f'waiting for {num_stacks_pending} stacks to be deleted: {stacks_pending} ...')
                time.sleep(15)

        return delete_failed == 0

    def delete_identity_provider_stacks(self):
        stack_names = []
        for stack in self.identity_provider_stacks:
            stack_name = Utils.get_value_as_string('StackName', stack)
            stack_names.append(stack_name)
            self.delete_cloud_formation_stack(stack_name)

        deletion_status = self.check_stack_deletion_status(stack_names)
        if not deletion_status:
            self.context.error('failed to delete CloudFormation stacks. abort!')
            raise SystemExit(1)

    def delete_cloud_formation_stacks(self):
        stack_names = []
        for stack in self.cloud_formation_stacks:
            stack_name = Utils.get_value_as_string('StackName', stack)
            stack_names.append(stack_name)
            self.delete_cloud_formation_stack(stack_name)

        deletion_status = self.check_stack_deletion_status(stack_names)
        if not deletion_status:
            self.context.error('failed to delete CloudFormation stacks. abort!')
            raise SystemExit(1)

    def find_dynamodb_tables(self):
        last_evaluated_table_name = None
        while True:
            if Utils.is_empty(last_evaluated_table_name):
                list_tables_result = self.context.aws().dynamodb().list_tables()
            else:
                list_tables_result = self.context.aws().dynamodb().list_tables(ExclusiveStartTableName=last_evaluated_table_name)
            tables = Utils.get_value_as_list('TableNames', list_tables_result, [])
            for table_name in tables:
                if table_name.startswith(f'{self.cluster_name}.'):
                    self.dynamodb_tables.append(table_name)

            last_evaluated_table_name = Utils.get_value_as_string('LastEvaluatedTableName', list_tables_result, None)
            if Utils.is_empty(last_evaluated_table_name):
                break

    def print_dynamodb_tables(self):
        dynamodb_table = PrettyTable(['Table Name'])
        dynamodb_table.align = 'l'
        tables = self.dynamodb_tables
        for table in tables:
            dynamodb_table.add_row([table])

        if len(tables) > 0:
            print(dynamodb_table)
        print(f'{len(tables)} tables will be deleted.')

    def delete_dynamodb_tables(self):
        for table in self.dynamodb_tables:
            self.delete_dynamo_table(table)

        # Cleanup Cloudwatch Alarms for all tables
        self.delete_cloudwatch_alarms()


    def delete_cloudwatch_alarms(self):
        alarms_to_delete = []
        # Generate our list of Cloudwatch alarms that pertain to us
        # This will grab all alarms for the present cluster as well
        # as any previous clusters with the same name. This can clean up
        # previous versions that didn't have alarm cleanup
        try:
            paginator = self.context.aws().cloudwatch().get_paginator('describe_alarms')
            page_iterator = paginator.paginate(AlarmNamePrefix=f'TargetTracking-table/{self.cluster_name}')
            for page in page_iterator:
                for metric in page.get('MetricAlarms', []):
                    alarm_name = metric.get('AlarmName', '')
                    alarm_namespace = metric.get('Namespace', 'unknown-namespace')
                    if alarm_namespace != 'AWS/DynamoDB':
                        continue

                    for dim in metric.get('Dimensions', []):
                        dim_name = dim.get('Name', '')
                        dim_value = dim.get('Value', '')

                        # Only concerned for the DDB alarms
                        if dim_name != 'TableName':
                            continue
                        # Make sure it is a DDB table we expect as part of our schema
                        if dim_value not in self.dynamodb_tables:
                            self.context.warning(f'Found a mismatched CloudWatch alarm / DynamoDB table name: {alarm_name}')
                            continue
                        #
                        if alarm_name in alarms_to_delete:
                            continue
                        # If we make it this far - it is the alarm we are looking for, append.
                        alarms_to_delete.append(alarm_name)
        except Exception as e:
            self.context.warning(f'Exception ({e}) trying to get CloudWatch Alarms for {self.cluster_name}')
            raise e

        # Now delete the list
        if len(alarms_to_delete) > 0:
            self.context.info(f'Found {len(alarms_to_delete):,} CloudWatch alarms to delete.')
            # delete_alarms() operates on 100 at a time, so we chunk them
            # in case we have many alarms to delete.
            try:
                for chunk in range(0, len(alarms_to_delete), 100):
                    delete_resp = self.context.aws().cloudwatch().delete_alarms(AlarmNames=alarms_to_delete[chunk:chunk+100])
                    if delete_resp and delete_resp.get('ResponseMetadata', {}).get('HTTPStatusCode', 400) == 200:
                        self.context.info(f'Successfully deleted CloudWatch alarms batch #{chunk} for {self.cluster_name}')
                    else:
                        self.context.warning(f'Error during delete of CloudWatch Alarms batch #{chunk} for {self.cluster_name}: {delete_resp}')
            except Exception as e:
                self.context.warning(f'Exception ({e}) during delete of CloudWatch Alarms for {self.cluster_name}')
                raise e
            self.context.success(f'Deleted CloudWatch alarms for: {self.cluster_name}')
        else:
            self.context.info('Did not find any Cloudwatch alarms to delete...')

    def find_cloudwatch_logs(self):
        self.context.info('Searching for CloudWatch log groups to be deleted ...')
        paginator = self.context.aws().logs().get_paginator('describe_log_groups')

        for prefix in {f'/{self.cluster_name}', f'/aws/lambda/{self.cluster_name}'}:
            self.context.info(f'Looking for Cloudwatch logs in {prefix}')
            page_iterator = paginator.paginate(logGroupNamePrefix=prefix)
            for page in page_iterator:
                for log_group in page["logGroups"]:
                    log_group_name = Utils.get_value_as_string('logGroupName', log_group)
                    log_group_bytes = Utils.get_value_as_int('storedBytes', log_group, default=0)
                    if Utils.is_empty(log_group_name):
                        continue
                    self.cloudwatch_logs.append({'name': log_group_name, 'size': log_group_bytes})

    def print_cloudwatch_logs(self):
        total_size = 0
        cloudwatch_logs_table = PrettyTable(['Log Group Name', 'Size'])
        cloudwatch_logs_table.align = 'l'
        logs = self.cloudwatch_logs
        for log in logs:
            log_group_size = SocaMemory(value=log.get('size', 0), unit=SocaMemoryUnit.BYTES)
            total_size += log.get('size', 0)
            cloudwatch_logs_table.add_row([log.get('name'), log_group_size.as_unit(SocaMemoryUnit.MB)])

        if len(logs) > 0:
            print(cloudwatch_logs_table)

        total_size_mb = SocaMemory(value=total_size, unit=SocaMemoryUnit.BYTES)
        print(f'{len(logs)} log groups will be deleted. Total Size: {total_size_mb.as_unit(SocaMemoryUnit.MB)}')

    def delete_cloudwatch_log_groups(self):
        for log_group in self.cloudwatch_logs:
            try:
                log_group_name = log_group.get('name')
                print(f'deleting cloudwatch log group: {log_group_name} ...')
                self.context.aws().logs().delete_log_group(logGroupName=log_group_name)
                self.context.success(f'deleted log group: {log_group_name}')
                time.sleep(.1)
            except botocore.exceptions.BotoCoreError as e:
                raise e

    def delete_bootstrap_and_s3_bucket(self):
        stack_name = self.get_bootstrap_stack_name()
        self.delete_cloud_formation_stack(stack_name)
        self.delete_s3_bucket()

    def delete_cluster_stack(self):
        stack_names = []
        for cluster_stack in self.cluster_stacks:
            stack_name = Utils.get_value_as_string('StackName', cluster_stack)
            stack_names.append(stack_name)
            self.delete_cloud_formation_stack(stack_name)

        deletion_status = self.check_stack_deletion_status(stack_names)
        if not deletion_status:
            self.context.error('failed to delete cluster stack. abort!')
            raise SystemExit(1)

    def delete_s3_bucket(self):
        try:

            # get s3 bucket name
            bucket_name = None
            if self.cluster_config_db is not None:
                config_entry = self.cluster_config_db.get_config_entry('cluster.cluster_s3_bucket')

                if Utils.is_not_empty(config_entry):
                    bucket_name = config_entry['value']

            if Utils.is_empty(bucket_name):
                account_id = self.context.aws().aws_account_id()
                bucket_name = str(self.cluster_name) + '-cluster-' + self.aws_region + '-' + account_id

            s3_bucket = self.context.aws().s3_bucket()
            bucket = s3_bucket.Bucket(bucket_name)
            if bucket.creation_date:
                print(f'found cluster S3 bucket: {bucket_name}')
            else:
                self.context.warning('cluster bucket not found. skip.')
                return

            print(f'deleting S3 bucket: {bucket_name} for cluster ...')

            # create s3 bucket resource and delete all versions in the bucket
            # This includes current versions - no explicit object list needed
            bucket.object_versions.all().delete()
            time.sleep(5)

            # delete the bucket itself
            self.context.aws().s3().delete_bucket(Bucket=bucket_name)

            self.context.success(f'bucket {bucket_name} deleted successfully')

        except botocore.exceptions.BotoCoreError as e:
            raise e

    def delete_backup_vault_recovery_points(self):
        """
        delete all recovery points for the backup vault configured for the cluster.
        the implementation assumes the backup vault will be named as: CLUSTER_NAME-cluster-backup-vault.
        """
        # backup vault must be of below name format
        backup_vault_name = f'{self.cluster_name}-cluster-backup-vault'
        try:

            # basic check to find if backup vault exists
            self.context.aws().backup().describe_backup_vault(
                BackupVaultName=backup_vault_name
            )

            total_recovery_points = 0
            total_deleted = 0

            bu_paginator = self.context.aws().backup().get_paginator('list_recovery_points_by_backup_vault')
            bu_iterator = bu_paginator.paginate(BackupVaultName=backup_vault_name)

            for _page in bu_iterator:
                recovery_points = Utils.get_value_as_list('RecoveryPoints', _page, [])
                total_recovery_points += len(recovery_points)

            _rp_delete_start = Utils.current_time_ms()
            self.context.info(f"Deleting {len(recovery_points)} recovery points from AWS Backup...")
            for recovery_point in recovery_points:
                recovery_point_arn = Utils.get_value_as_string('RecoveryPointArn', recovery_point)

                # can be one of: 'COMPLETED'|'PARTIAL'|'DELETING'|'EXPIRED'
                # if status is not COMPLETED/EXPIRED, do not attempt to delete, but wait for deletion or backup completion.
                recovery_point_status = Utils.get_value_as_string('Status', recovery_point)
                if recovery_point_status not in ('COMPLETED', 'EXPIRED'):
                    continue

                self.context.info(f'deleting recovery point: {recovery_point_arn} ...')
                self.context.aws().backup().delete_recovery_point(
                    BackupVaultName=backup_vault_name,
                    RecoveryPointArn=recovery_point_arn
                )
                total_deleted += 1
                time.sleep(.1)

            _rp_delete_end = Utils.current_time_ms()
            _run_time_ms = int((_rp_delete_end - _rp_delete_start) / 1_000)
            self.context.info(f'deleted {total_recovery_points} recovery points in {_run_time_ms} seconds.')

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                # possibly backups are not enabled for the cluster. skip
                pass
            else:
                raise e

    def validate_target_group(self, tg_arn: str) -> bool:
        if not tg_arn:
            return False
        tag_description = self.context.aws().elbv2().describe_tags(ResourceArns=[tg_arn]).get('TagDescriptions', [None])[0]

        if not tag_description:
            return False

        tags = tag_description.get('Tags', [])
        for tag in tags:
            if tag.get('Key') == constants.IDEA_TAG_ENVIRONMENT_NAME and tag.get('Value') == self.cluster_name:
                return True
        return False

    def delete_target_groups(self):
        self.context.info(
            f'Searching for target groups to be deleted...')

        try:
            target_group_arns = []
            tg_paginator = self.context.aws().elbv2().get_paginator('describe_target_groups')
            tg_iterator = tg_paginator.paginate()

            for page in tg_iterator:
                for tg in page.get('TargetGroups', []):
                    tg_name = tg.get('TargetGroupName', '')
                    tg_arn = tg.get('TargetGroupArn', '')
                    if tg_name.startswith(self.cluster_name) and self.validate_target_group(tg_arn):
                        self.context.info(f'Target group : {tg_name}')
                        target_group_arns.append(tg_arn)

            for target_group_arn in target_group_arns:
                self.context.aws().elbv2().delete_target_group(TargetGroupArn=target_group_arn)

        except Exception as e:
            self.context.error(f'Error deleting target groups: {e}')

    def invoke(self):

        # Finding ec2 instances
        self.find_ec2_instances()

        if Utils.is_not_empty(self.ec2_instances):
            self.print_ec2_instances(self.ec2_instances)
            print(f'{len(self.ec2_instances)} ec2 instances will be terminated.')

        # Finding CloudFormation stacks
        self.find_cloud_formation_stacks()
        self.print_cloud_formation_stacks()

        if not self.force:
            confirm = self.context.prompt(f'Are you sure you want to delete cluster: {self.cluster_name}, region: {self.aws_region} ?')
            if not confirm:
                return

        self.invoke_app_app_module_clean_up()

        if Utils.is_not_empty(self.termination_protected_ec2_instances):
            self.print_ec2_instances(self.termination_protected_ec2_instances)
            print(f'found {len(self.termination_protected_ec2_instances)} EC2 instances with termination protection enabled.')
            if not self.force:
                confirm = self.context.prompt('Are you sure you want to disable termination protection for above instances ?')
                if not confirm:
                    return

        self.detach_vpc_from_lambda_functions()

        self.delete_ec2_instances()
        self.delete_cloud_formation_stacks()

        # Delete identity-provider stack - removing UserPool protection
        self.delete_identity_provider_stacks()

        # delete backups if applicable
        if self.delete_backups or self.delete_all:
            confirm_delete_backups = self.force
            if not self.force:
                confirm_delete_backups = self.context.prompt(f'Are you sure you want to delete all the backup recovery points associated with the cluster: 'f'{self.cluster_name}?')

            if confirm_delete_backups:
                self.delete_backup_vault_recovery_points()

        self.delete_cluster_stack()

        if self.delete_bootstrap or self.delete_all:
            confirm_delete_bootstrap = self.force
            if not self.force:
                confirm_delete_bootstrap = self.context.prompt(f'Are you sure you want to delete the bootstrap stack and S3 Bucket associated with the cluster: 'f'{self.cluster_name}? This action is not reversible.')

            if confirm_delete_bootstrap:
                self.delete_bootstrap_and_s3_bucket()

        #Required here because QUIC support modifies the target groups which cloudformation cannot recognize
        #At this point load balancers and listeners have been deleted
        self.context.info(f'Deleting target groups...')
        self.delete_target_groups()
        
        if self.delete_databases or self.delete_all:
            self.find_dynamodb_tables()
            if Utils.is_not_empty(self.dynamodb_tables):
                self.print_dynamodb_tables()

                confirm_delete_databases = self.force
                if not self.force:
                    confirm_delete_databases = self.context.prompt(f'Are you sure you want to delete all dynamodb tables associated with the cluster: 'f'{self.cluster_name}?')

                if confirm_delete_databases:
                    self.delete_dynamodb_tables()

        if self.delete_cloudwatch_logs or self.delete_all:
            self.find_cloudwatch_logs()
            if Utils.is_not_empty(self.cloudwatch_logs):
                self.print_cloudwatch_logs()

                confirm_delete_cloudwatch_logs = self.force
                if not self.force:
                    confirm_delete_cloudwatch_logs = self.context.prompt(f'Are you sure you want to delete all cloudwatch logs associated with the cluster: 'f'{self.cluster_name}?')

                if confirm_delete_cloudwatch_logs:
                    self.delete_cloudwatch_log_groups()

        
