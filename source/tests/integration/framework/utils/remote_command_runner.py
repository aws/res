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

import logging
from enum import Enum
from typing import Any, Optional

import boto3

logger = logging.getLogger(__name__)


class EC2InstancePlatform(Enum):
    LINUX = "linux"
    WINDOWS = "windows"


class RemoteCommandRunner:
    def __init__(
        self,
        region: str,
        platform: EC2InstancePlatform = EC2InstancePlatform.LINUX,
        output_bucket: Optional[str] = None,
    ):
        session = boto3.session.Session(region_name=region)
        self._ssm_client = session.client("ssm")
        self._s3_resource = session.resource("s3")
        self._output_bucket = output_bucket

        if platform == EC2InstancePlatform.LINUX:
            self._document_name = "AWS-RunShellScript"
        elif platform == EC2InstancePlatform.WINDOWS:
            self._document_name = "AWS-RunPowerShellScript"

    def run(self, instance_id: str, commands: list[str]) -> Any:
        logger.debug(f"sending commands {commands} to instance {instance_id}")

        if self._output_bucket:
            cmd_result = self._ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=self._document_name,
                Parameters={"commands": commands},
                OutputS3BucketName=self._output_bucket,
            )
        else:
            cmd_result = self._ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=self._document_name,
                Parameters={"commands": commands},
            )

        command_id = cmd_result.get("Command", {}).get("CommandId", "")

        waiter = self._ssm_client.get_waiter("command_executed")
        waiter.wait(
            CommandId=command_id,
            InstanceId=instance_id,
        )

        get_output_result = self._ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )

        output = (
            self._read_s3_output(get_output_result.get("StandardOutputUrl"))
            if self._output_bucket
            else get_output_result.get("StandardOutputContent")
        )
        logger.debug(f"remote commands output: {output}")

        return output

    def _read_s3_output(self, s3_url: str) -> Any:
        sections = s3_url.split("/")
        # Verify that the url includes the s3 bucket name and object key
        assert len(sections) > 5, f"invalid remote command output URL: {s3_url}"

        bucket_name = sections[3]
        ssm_output_object_key = "/".join(sections[4:])
        logger.debug(
            f"remote command output bucket: {bucket_name} object key: {ssm_output_object_key}"
        )

        ssm_output_object = self._s3_resource.Object(
            bucket_name, ssm_output_object_key
        ).get()
        return ssm_output_object.get("Body").read().decode("utf-8")
