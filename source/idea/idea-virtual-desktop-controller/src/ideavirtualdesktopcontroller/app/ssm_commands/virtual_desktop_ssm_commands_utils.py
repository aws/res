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
from typing import List

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopBaseOS
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB, VirtualDesktopSSMCommand, VirtualDesktopSSMCommandType


class VirtualDesktopSSMCommandsUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopSSMCommandsDB):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-ssm-commands-utils')
        self._ssm_commands_db = db
        self._ssm_client = self.context.aws().ssm()

    def submit_ssm_command_to_resume_session(self, instance_id: str, idea_session_id: str, idea_session_owner: str, commands: List[str], document_name: str) -> str:
        response = self._ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName=document_name,
            Comment=f'idea_session_id: {idea_session_id}, owner: {idea_session_owner}',
            Parameters={'commands': commands},
            ServiceRoleArn=self.context.config().get_string('virtual-desktop-controller.ssm_commands_pass_role_arn', required=True),
            NotificationConfig={
                'NotificationArn': self.context.config().get_string('virtual-desktop-controller.ssm_commands_sns_topic_arn', required=True),
                'NotificationEvents': ['All'],
                'NotificationType': 'Invocation'
            },
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True,
                'CloudWatchLogGroupName': f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/resume'
            },
            OutputS3BucketName=self.context.config().get_string('cluster.cluster_s3_bucket', required=True),
            OutputS3KeyPrefix=f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/resume'
        )
        # self._logger.info(f'response is {response}')
        command_id = Utils.get_value_as_string('CommandId', Utils.get_value_as_dict('Command', response, {}), '')
        _ = self._ssm_commands_db.create(VirtualDesktopSSMCommand(
            command_id=command_id,
            command_type=VirtualDesktopSSMCommandType.RESUME_SESSION,
            additional_payload={
                'idea_session_id': idea_session_id,
                'idea_session_owner': idea_session_owner,
                'instance_id': instance_id
            }
        ))
        self._logger.info(f'SSM command to resume session sent for {idea_session_id}:, owner: {idea_session_owner}.')
        return command_id

    def submit_ssm_command_to_disable_userdata_execution_on_windows(self, instance_id: str, idea_session_id: str, idea_session_owner: str) -> str:
        response = self._ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunPowerShellScript',
            Comment='Enabling userdata execution for Windows EC2 Instance',
            Parameters={'commands': ['Unregister-ScheduledTask -TaskName "Amazon Ec2 Launch - Instance Initialization" -Confirm$False']},
            ServiceRoleArn=self.context.config().get_string('virtual-desktop-controller.ssm_commands_pass_role_arn', required=True),
            NotificationConfig={
                'NotificationArn': self.context.config().get_string('virtual-desktop-controller.ssm_commands_sns_topic_arn', required=True),
                'NotificationEvents': ['All'],
                'NotificationType': 'Invocation'
            },
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True,
                'CloudWatchLogGroupName': f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/disable-userdata'
            },
            OutputS3BucketName=self.context.config().get_string('cluster.cluster_s3_bucket', required=True),
            OutputS3KeyPrefix=f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/disable-userdata'
        )
        # self._logger.info(f'response is {response}')
        command_id = Utils.get_value_as_string('CommandId', Utils.get_value_as_dict('Command', response, {}), '')
        _ = self._ssm_commands_db.create(VirtualDesktopSSMCommand(
            command_id=command_id,
            command_type=VirtualDesktopSSMCommandType.WINDOWS_DISABLE_USERDATA_EXECUTION,
            additional_payload={
                'idea_session_id': idea_session_id,
                'idea_session_owner': idea_session_owner,
                'instance_id': instance_id
            }
        ))
        self._logger.info(f'SSM command to disable userdata execution sent to {instance_id}.')
        return command_id

    def submit_ssm_command_to_enable_userdata_execution_on_windows(self, instance_id: str, idea_session_id: str, idea_session_owner: str, software_stack_id: str) -> str:
        response = self._ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunPowerShellScript',
            Comment='Enabling userdata execution for Windows EC2 Instance',
            Parameters={'commands': ['C:\\ProgramData\\Amazon\\EC2-Windows\\Launch\\Scripts\\InitializeInstance.ps1 -Schedule']},
            ServiceRoleArn=self.context.config().get_string('virtual-desktop-controller.ssm_commands_pass_role_arn', required=True),
            NotificationConfig={
                'NotificationArn': self.context.config().get_string('virtual-desktop-controller.ssm_commands_sns_topic_arn', required=True),
                'NotificationEvents': ['All'],
                'NotificationType': 'Invocation'
            },
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True,
                'CloudWatchLogGroupName': f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/enable-userdata'
            },
            OutputS3BucketName=self.context.config().get_string('cluster.cluster_s3_bucket', required=True),
            OutputS3KeyPrefix=f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/enable-userdata'
        )
        # self._logger.info(f'response is {response}')
        command_id = Utils.get_value_as_string('CommandId', Utils.get_value_as_dict('Command', response, {}), '')
        _ = self._ssm_commands_db.create(VirtualDesktopSSMCommand(
            command_id=command_id,
            command_type=VirtualDesktopSSMCommandType.WINDOWS_ENABLE_USERDATA_EXECUTION,
            additional_payload={
                'idea_session_id': idea_session_id,
                'idea_session_owner': idea_session_owner,
                'instance_id': instance_id,
                'software_stack_id': software_stack_id
            }
        ))
        self._logger.info(f'SSM command to enable userdata execution sent to {instance_id}.')
        return command_id

    def submit_ssm_command_to_get_cpu_utilization(self, instance_id: str, idea_session_id: str, idea_session_owner: str, base_os: VirtualDesktopBaseOS):
        if base_os == VirtualDesktopBaseOS.WINDOWS:
            document_name = 'AWS-RunPowerShellScript'
            commands = [
                "$CPUAveragePerformanceLast10Secs = (GET-COUNTER -Counter \"\\Processor(_Total)\\% Processor Time\" -SampleInterval 2 -MaxSamples 5 |select -ExpandProperty countersamples | select -ExpandProperty cookedvalue | Measure-Object -Average).average",
                "$output = @{}",
                "$output[\"CPUAveragePerformanceLast10Secs\"] = $CPUAveragePerformanceLast10Secs",
                "$output | ConvertTo-Json"
            ]
        else:
            document_name = 'AWS-RunShellScript'
            commands = [
                "CPUAveragePerformanceLast10Secs=$(top -d 5 -b -n2 | grep 'Cpu(s)' |tail -n 1 | awk '{print $2 + $4}')",
                "echo '{\"CPUAveragePerformanceLast10Secs\": '"'$CPUAveragePerformanceLast10Secs'"'}'"
            ]

        response = self._ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName=document_name,
            Comment=f'Checking CPU Utilization for {instance_id}',
            Parameters={'commands': commands},
            ServiceRoleArn=self.context.config().get_string('virtual-desktop-controller.ssm_commands_pass_role_arn', required=True),
            NotificationConfig={
                'NotificationArn': self.context.config().get_string('virtual-desktop-controller.ssm_commands_sns_topic_arn', required=True),
                'NotificationEvents': ['All'],
                'NotificationType': 'Invocation'
            },
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True,
                'CloudWatchLogGroupName': f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/cpu-utilization'
            },
            OutputS3BucketName=self.context.config().get_string('cluster.cluster_s3_bucket', required=True),
            OutputS3KeyPrefix=f'/{self.context.cluster_name()}/{self.context.module_id()}/dcv-session/{idea_session_id}/cpu-utilization'
        )
        # self._logger.info(f'response is {response}')
        command_id = Utils.get_value_as_string('CommandId', Utils.get_value_as_dict('Command', response, {}), '')
        _ = self._ssm_commands_db.create(VirtualDesktopSSMCommand(
            command_id=command_id,
            command_type=VirtualDesktopSSMCommandType.CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION,
            additional_payload={
                'idea_session_id': idea_session_id,
                'idea_session_owner': idea_session_owner,
                'instance_id': instance_id
            }
        ))
        self._logger.info(f'SSM command to check CPU Utilization sent to {instance_id}.')
        return command_id
