#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import logging
import re
from typing import Any, Dict, Optional

import boto3
import jwt
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# 1 hour expiration time
TEMPORARY_CREDENTIALS_TIME_IN_SECONDS = 3600


class Utils:

    @staticmethod
    def get_instance_id_from_request_context(request_context: Dict[str, Any]) -> Any:
        user_arn = Utils.get_user_arn_from_request_context(request_context)
        return Utils.get_instance_id_from_user_arn(user_arn) if user_arn else None

    @staticmethod
    def get_user_arn_from_request_context(request_context: Dict[str, Any]) -> Any:
        return request_context.get("identity", {}).get("userArn")

    @staticmethod
    def get_instance_id_from_user_arn(user_arn: str) -> Any:
        pattern = (
            r"arn:aws(?:-cn|-us-gov)?:sts::\d+:assumed-role\/[^\/]+\/(i-[a-f0-9]+)"
        )
        match = re.search(pattern, user_arn)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def get_source_ip_from_request_context(request_context: Dict[str, Any]) -> Any:
        return request_context.get("identity", {}).get("sourceIp")

    @staticmethod
    def get_filesystem_name_from_request_context(event: Dict[str, Any]) -> Any:
        return event.get("queryStringParameters", {}).get("filesystemName")

    @staticmethod
    def validate_instance_origin(instance_id: str, source_ip: str) -> bool:
        ec2 = boto3.client("ec2")
        try:
            response = ec2.describe_instances(InstanceIds=[instance_id])
        except Exception as e:
            logger.error(f"Error describing instance: {e}")
            return False
        reservations = response.get("Reservations", [])
        if len(reservations) != 1:
            return False
        instance = reservations[0]["Instances"][0]
        if instance.get("PrivateIpAddress") != source_ip:
            return False
        return True

    @staticmethod
    def verify_jwt_token(token: Any, secret: Any) -> Any:
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def get_bootstrap_token_from_request_context(
        event: Dict[str, Any]
    ) -> Optional[Any]:
        return event.get("queryStringParameters", {}).get("bootstrapToken")

    @staticmethod
    def get_bootstrap_temporary_credentials(
        role_arn: str, role_session_name: str
    ) -> Optional[Dict[str, Any]]:
        sts = boto3.client("sts")
        try:
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                DurationSeconds=TEMPORARY_CREDENTIALS_TIME_IN_SECONDS,
            )
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error assuming role: {e}")
            return None

        credentials = response["Credentials"]
        return {
            "Version": 1,
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretAccessKey": credentials["SecretAccessKey"],
            "SessionToken": credentials["SessionToken"],
            "Expiration": credentials["Expiration"].isoformat(),
        }

    @staticmethod
    def get_custom_broker_secret(secret_name: str, region_name: str) -> Optional[Any]:
        session = boto3.session.Session()

        client = session.client(service_name="secretsmanager", region_name=region_name)

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        except Exception as e:
            raise e
        else:
            if "SecretString" in get_secret_value_response:
                secret = get_secret_value_response["SecretString"]
                return secret
            else:
                decoded_binary_secret = base64.b64decode(
                    get_secret_value_response["SecretBinary"]
                )
                return decoded_binary_secret

    @staticmethod
    def generate_session_policy(
        read_only: bool, bucket_arn: str, prefix: Optional[str] = None
    ) -> str:
        bucket_arn = bucket_arn.rstrip("/")
        statements = []
        list_bucket_action = ["s3:ListBucket"]
        read_only_actions = [
            "s3:GetObject",
        ]
        write_only_actions = [
            "s3:PutObject",
            "s3:AbortMultipartUpload",
            "s3:DeleteObject",
        ]
        if read_only:
            actions = read_only_actions
        else:
            actions = read_only_actions + write_only_actions

        if prefix:
            prefix = prefix.rstrip("/")
            full_arn_bucket_arn = f"{bucket_arn}/{prefix}"
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": f"{full_arn_bucket_arn}/*",
                }
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": list_bucket_action,
                    "Resource": bucket_arn,
                    "Condition": {"StringLike": {"s3:prefix": f"{prefix}/*"}},  # type: ignore
                }
            )
        else:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": list_bucket_action + actions,
                    "Resource": [f"{bucket_arn}/*", bucket_arn],
                }
            )
        policy = {"Version": "2012-10-17", "Statement": statements}

        return json.dumps(policy, indent=4)

    @staticmethod
    def get_temporary_credentials(
        role_arn: str,
        role_session_name: str,
        read_only: bool,
        bucket_arn: str,
        prefix: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sts = boto3.client("sts")
        try:
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                DurationSeconds=TEMPORARY_CREDENTIALS_TIME_IN_SECONDS,
                Policy=Utils.generate_session_policy(read_only, bucket_arn, prefix),
            )
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error assuming role: {e}")
            return None

        credentials = response["Credentials"]
        return {
            "Version": 1,
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretAccessKey": credentials["SecretAccessKey"],
            "SessionToken": credentials["SessionToken"],
            "Expiration": credentials["Expiration"].isoformat(),
        }

    @staticmethod
    def extract_bucket_arn_without_prefix(bucket_arn: str) -> Optional[str]:
        match = re.match(r"^(arn:aws(?:-cn|-us-gov)?:(s3:::)[^/]+)", bucket_arn)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def extract_prefix_from_bucket_arn(bucket_arn: str) -> Optional[str]:
        match = re.match(r"^arn:aws(?:-cn|-us-gov)?:s3:::[^/]+/(.*)", bucket_arn)
        if match:
            return match.group(1)
        return None
