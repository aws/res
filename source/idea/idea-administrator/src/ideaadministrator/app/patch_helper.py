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


import ideaadministrator
from ideadatamodel import exceptions, constants, EC2Instance
from ideasdk.utils import Utils

from ideasdk.context import SocaCliContext, SocaContextOptions

from typing import List
import os
import time
from prettytable import PrettyTable

PATCH_LOG = '/root/bootstrap/logs/patch.log'


class PatchHelper:

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str, component: str,
                 instance_selector: str,
                 module_id: str, package_uri: str, force: bool,
                 patch_command: str):

        if Utils.is_empty(cluster_name):
            raise exceptions.invalid_params('cluster_name is required')
        if Utils.is_empty(aws_region):
            raise exceptions.invalid_params('aws_region is required')
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('module_id is required')

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.component = component
        self.instance_selector = instance_selector
        self.module_id = module_id
        self.user_package_uri = package_uri
        self.force = force
        self.patch_command = patch_command

        self.context = SocaCliContext(options=SocaContextOptions(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            enable_aws_client_provider=True
        ))

        module_info = self.context.get_cluster_module_info(module_id)
        if module_info is None:
            raise exceptions.general_exception(f'module not found: {module_id}')
        module_type = module_info['type']
        if module_type != 'app':
            raise exceptions.general_exception(f'patching is not supported for module: {module_id}, type: {module_type}')
        self.module_name = module_info['name']

        status = module_info['status']
        if status != 'deployed':
            raise exceptions.general_exception(f'cannot patch module. module: {module_id} is not yet deployed.')

    def try_get_s3_package_uri(self) -> str:
        """
        if package uri is provided by the user, check if the package uri is local or s3 path.
            if package is local, upload to cluster's s3 bucket and return uri

        if package uri is not provided, find the local package uri for current release, upload to s3 and return the s3 path.
            if running in dev mode from sources, package uri is: <PROJECT_ROOT>/dist/<package>.tar.gz
            if running in docker container, package uri is: /root/.idea/downloads/<package>.tar.gz

        :return: s3 path
        """
        if Utils.is_not_empty(self.user_package_uri):
            package_uri = self.user_package_uri
        else:

            if ideaadministrator.props.is_dev_mode():
                package_dist_dir = ideaadministrator.props.dev_mode_project_dist_dir
            else:
                package_dist_dir = ideaadministrator.props.soca_downloads_dir

            package_uri = os.path.join(package_dist_dir,
                                       f'idea-{self.module_name}-{ideaadministrator.props.current_release_version}.tar.gz')

        if package_uri.startswith('s3://'):
            return package_uri

        if not Utils.is_file(package_uri):
            raise exceptions.file_not_found(f'release package not found: {package_uri}')

        cluster_s3_bucket = self.context.config().get_string('cluster.cluster_s3_bucket', required=True)

        s3_path = f'idea/patches/{os.path.basename(package_uri)}'
        s3_package_uri = f's3://{cluster_s3_bucket}/{s3_path}'
        self.context.info(f'uploading package: {package_uri} to {s3_package_uri} ...')
        self.context.aws().s3().upload_file(
            Bucket=cluster_s3_bucket,
            Filename=package_uri,
            Key=s3_path
        )
        return s3_package_uri

    def get_patch_run_command(self, package_uri: str) -> str:
        if self.module_name in (
            constants.MODULE_DIRECTORYSERVICE,
            constants.MODULE_CLUSTER_MANAGER,
            constants.MODULE_SCHEDULER
        ):
            return f'sudo /bin/bash /root/bootstrap/latest/{self.module_name}/install_app.sh {package_uri} >> {PATCH_LOG}'
        elif self.module_name == constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER:
            if Utils.is_empty(self.component):
                return f'sudo /bin/bash /root/bootstrap/latest/{self.module_name}/install_app.sh {package_uri} >> {PATCH_LOG}'
            else:
                # TODO: Deprecate
                return f'sudo /bin/bash /root/bootstrap/latest/reverse-proxy-server/install_app.sh {package_uri} >> {PATCH_LOG}'

    def print_ec2_instance_table(self, instances: List[EC2Instance]):
        table = PrettyTable(['Instance Id', 'Instance Name', 'Host Name', 'Private IP', 'State'])
        table.align = 'l'

        for instance in instances:
            table.add_row([instance.instance_id, instance.get_tag('Name'), instance.private_dns_name_fqdn, instance.private_ip_address, instance.state])

        print(table)

    def patch_app(self):

        self.context.info('searching for applicable ec2 instances ...')
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
                    'Values': [self.module_id]
                },
                {
                    'Name': f'tag:{constants.IDEA_TAG_NODE_TYPE}',
                    'Values': ['app']
                }
            ]
        )

        instances_to_patch = []
        instances_cannot_be_patched = []

        reservations = Utils.get_value_as_list('Reservations', describe_instances_result, [])
        for reservation in reservations:
            instances = Utils.get_value_as_list('Instances', reservation)
            for instance in instances:
                ec2_instance = EC2Instance(instance)
                if ec2_instance.state == 'running':
                    if Utils.is_empty(self.instance_selector) or self.instance_selector == 'all':
                        instances_to_patch.append(ec2_instance)
                    else:
                        if self.instance_selector == 'any':
                            instances_to_patch.append(ec2_instance)
                            break
                else:
                    instances_cannot_be_patched = ec2_instance

        if len(instances_cannot_be_patched) > 0:
            self.context.warning('Below instances cannot be patched as the instances are not running: ')
            self.print_ec2_instance_table(instances_cannot_be_patched)

        if len(instances_to_patch) == 0:
            self.context.warning('No instances found to be patched. Abort.')
            return

        self.print_ec2_instance_table(instances_to_patch)
        if not self.force:
            confirm = self.context.prompt(f'Are you sure you want to patch the above running ec2 instances for module: {self.module_name}?')
            if not confirm:
                self.context.info('Patch aborted!')
                return

        with self.context.spinner('patching ec2 instances via AWS Systems Manager (Run Command) ... '):

            if Utils.is_empty(self.patch_command):
                package_uri = self.try_get_s3_package_uri()
                patch_command = self.get_patch_run_command(package_uri)
            else:
                patch_command = self.patch_command
            print(f'patch command: {patch_command}')

            instance_ids = []
            for ec2_instance in instances_to_patch:
                instance_ids.append(ec2_instance.instance_id)

            send_command_result = self.context.aws().ssm().send_command(
                InstanceIds=instance_ids,
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        f'sudo echo "# $(date) executing patch ..." >> {PATCH_LOG}',
                        patch_command,
                        f'sudo tail -10 {PATCH_LOG}'
                    ]
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

                if len(command_invocations) > 0:
                    self.context.info(f'Patching completed on {completed_count} out of {len(command_invocations)} instances')
                if completed_count == len(command_invocations) and len(command_invocations) > 0:
                    break

                time.sleep(10)

        list_command_invocations_result = self.context.aws().ssm().list_command_invocations(
            CommandId=command_id,
            Details=True
        )
        command_invocations = list_command_invocations_result['CommandInvocations']

        instance_id_to_command_invocations = {}
        for command_invocation in command_invocations:
            instance_id = command_invocation['InstanceId']
            instance_id_to_command_invocations[instance_id] = command_invocation

        self.context.info(f'Patch execution status for SSM Command Id: {command_id}')
        table = PrettyTable(['Instance Id', 'Instance Name', 'Host Name', 'Private IP', 'State', 'Patch Status'])
        table.align = 'l'
        for ec2_instance in instances_to_patch:
            command_invocation = instance_id_to_command_invocations[ec2_instance.instance_id]
            patch_status = command_invocation['Status']
            table.add_row([
                ec2_instance.instance_id,
                ec2_instance.get_tag('Name'),
                ec2_instance.private_dns_name_fqdn,
                ec2_instance.private_ip_address,
                ec2_instance.state,
                patch_status
            ])

        print(table)

        if failed_count > 0:
            self.context.error(f'Patch failed. Please check the patch logs for the instances at {PATCH_LOG}')
        else:
            self.context.success('Patch executed successfully. Please verify the patch functionality as per release notes / change log.')

    def apply(self):
        self.patch_app()
