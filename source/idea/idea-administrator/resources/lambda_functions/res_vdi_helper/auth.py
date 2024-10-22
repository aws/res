#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
import logging
import re
from typing import Any, Dict

import boto3
from res.resources import servers
from res.exceptions import ServerNotFound


from .actions import VDIHelperActions

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_user_arn_from_request_context(request_context):
    return request_context.get("identity", {}).get("userArn")


def get_instance_id_from_user_arn(user_arn: str):
    pattern = r'arn:aws(?:-cn|-us-gov)?:sts::\d+:assumed-role\/[^\/]+\/(i-[a-f0-9]+)'
    match = re.search(pattern, user_arn)
    if match:
        return match.group(1)
    return None


def get_instance_id_from_request_context(request_context):
    user_arn = get_user_arn_from_request_context(request_context)
    return get_instance_id_from_user_arn(user_arn) if user_arn else None


def get_source_ip_from_request_context(request_context):
    return request_context.get("identity", {}).get("sourceIp")


def validate_instance_origin(instance_id: str, source_ip: str):
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


def run_common_validations(instance_id: str, source_ip: str) -> bool:
    try:
        server_details = servers.get_server(instance_id=instance_id)
        owner_id = server_details.get(servers.SERVER_DB_SESSION_OWNER_KEY)
        session_id = server_details.get(servers.SERVER_DB_SESSION_ID_KEY)
        if not all([owner_id, session_id]):
            return False
        if not validate_instance_origin(instance_id, source_ip):
            return False
        return True
    except ServerNotFound as e:
        logger.error(f"Invalid instance, instance_id {instance_id} is not a VDI")
        return False


def get_action_level_validations() -> Dict[str, Any]:
    return {VDIHelperActions.VDI_AUTO_STOP: None}


def run_action_level_validations(action: str):
    action_validations = get_action_level_validations()

    if action not in action_validations:
        return False

    if callable(action_validations[action]):
        # Call additional validation methods assigned to each action if present
        return action_validations[action]()
    return True


def validate(event: Dict[str, Any]):
    logger.info(f"event: {event}")
    request_context = event["requestContext"]
    instance_id = get_instance_id_from_request_context(request_context)
    source_ip = get_source_ip_from_request_context(request_context)

    if not all([instance_id, source_ip]):
        raise ValueError("Invalid input parameters in the request context")

    is_valid_instance = run_common_validations(instance_id, source_ip)
    if not is_valid_instance:
        logger.error("Unauthorized access. Failed common validations.")
        return False

    action = event["queryStringParameters"].get("action", "")
    is_valid_action = run_action_level_validations(action)
    if not is_valid_action:
        logger.error("Unauthorized action or payload. Failed action level validation.")
        return False
    return True
