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

import os
import time
from res.resources import cluster_settings
from res.utils import aws_utils, logging_utils, instance_metadata_utils


logger = logging_utils.get_logger("bootstrap")

def send_sqs_host_messages(event_type: str):
    IDEA_SESSION_ID = os.environ.get("IDEA_SESSION_ID")  
    IDEA_SESSION_OWNER = os.environ.get("IDEA_SESSION_OWNER")
    CONTROLLER_EVENTS_QUEUE_URL = cluster_settings.get_setting('vdc.events_sqs_queue_url')
    instance_id = instance_metadata_utils.get_instance_id()
    
    logger.info(f"MESSAGE: {CONTROLLER_EVENTS_QUEUE_URL} - {event_type} - Instance Id: {instance_id}")
    current_timestamp = int(time.time() * 1000)
    
    payload = {
            "event_group_id": IDEA_SESSION_ID,
            "event_type": event_type,
            "detail": {
                "idea_session_id": IDEA_SESSION_ID,
                "idea_session_owner": IDEA_SESSION_OWNER,
                "instance_id": instance_id,
                "timestamp": str(current_timestamp)
            }
    }
    
    aws_utils.sqs_send_message(payload, CONTROLLER_EVENTS_QUEUE_URL, IDEA_SESSION_ID)
    