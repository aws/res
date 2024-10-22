#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import logging
from typing import Any, Dict

from res.resources import servers, sessions, vdi_management
from res.exceptions import UserSessionNotFound


from .actions import VDIHelperActions
from .auth import get_instance_id_from_request_context, validate

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:

    try:
        is_valid_event = validate(event)
        if not is_valid_event:
            raise RuntimeError("Unauthorized access")
        else:
            request_context = event["requestContext"]
            params = event["queryStringParameters"]
            action = params["action"]
            instance_id = get_instance_id_from_request_context(request_context)

            if action == VDIHelperActions.VDI_AUTO_STOP:
                transition_state = params.get("transition_state", "")
                handle_vdi_auto_stop(instance_id, transition_state)

    except Exception as e:
        logger.exception(f"Error in validating VDI Helper caller: {event}, error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    return {
        "statusCode": 200,
        "body": json.dumps(event),
    }


def handle_vdi_auto_stop(instance_id: str, transition_state: str) -> None:
    if not transition_state:
        raise RuntimeError("Request query parameters does not contain transition_state")
    if transition_state not in ["Stop", "Terminate"]:
        raise RuntimeError(f"Invalid transition state {transition_state}")
    logger.info(f"VDI auto stop for {instance_id} with transition_state {transition_state}")
    # Has been validated that the server is already present
    server = servers.get_server(instance_id=instance_id)
    session_id = server.get(servers.SERVER_DB_SESSION_ID_KEY)
    owner = server.get(servers.SERVER_DB_SESSION_OWNER_KEY)

    try:
        session = sessions.get_session(owner=owner, session_id=session_id)
        if transition_state == "Stop":
            session["is_idle"] = True
            vdi_management.stop_sessions(sessions=[session])
        else:
            vdi_management.terminate_sessions(sessions=[session])
    except UserSessionNotFound as e:
        raise RuntimeError(
            f"User session not found for VDI with instance id: {instance_id}."
        )
