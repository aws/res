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
"""
Analytics Sink Lambda:
This function is triggered by the analytics kinesis stream when any module submits an analytics event
"""
import base64
import os
import json
import logging
from opensearchpy import OpenSearch, helpers

opensearch_endpoint = os.environ.get('opensearch_endpoint')
if not opensearch_endpoint.startswith('https://'):
    opensearch_endpoint = f'https://{opensearch_endpoint}'

os_client = OpenSearch(
    hosts=[opensearch_endpoint],
    port=443,
    use_ssl=True,
    verify_certs=True
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, _):
    try:
        bulk_request_with_timestamp = []
        for record in event['Records']:
            analytics_entry = base64.b64decode(record["kinesis"]["data"])
            analytics_entry = json.loads(analytics_entry.decode())
            request = {
                "_id": analytics_entry["document_id"],
                "_index": analytics_entry["index_id"]
            }

            if analytics_entry["action"] == 'CREATE_ENTRY':
                # create new
                request["_op_type"] = "create"
                request["_source"] = analytics_entry["entry"]

            elif analytics_entry["action"] == 'UPDATE_ENTRY':
                # update existing
                request["_op_type"] = "update"
                request["doc"] = analytics_entry["entry"]
            else:
                # delete
                request["_op_type"] = "delete"

            bulk_request_with_timestamp.append((analytics_entry["timestamp"], request))

        bulk_request_with_timestamp_sorted = sorted(bulk_request_with_timestamp, key=lambda x: x[0])
        bulk_request = []
        for entry in bulk_request_with_timestamp_sorted:
            request = entry[1]
            logger.info(f'Submitting request for action: {request["_op_type"]} for document_id: {request["_id"]} to index {request["_index"]}')
            bulk_request.append(request)

        response = helpers.bulk(
            client=os_client,
            actions=bulk_request
        )
        logger.info(response)
    except Exception as e:
        logger.exception(f'Error while processing analytics request for event: {json.dumps(event)}, error: {e}')
