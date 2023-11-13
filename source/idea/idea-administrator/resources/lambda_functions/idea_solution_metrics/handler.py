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

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus

import json
import datetime
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http_client = HttpClient()

PHYSICAL_RESOURCE_ID = 'SolutionMetricsSO0280'

# Metric Keys that come in to the Lambda that are not relayed to the IDEA solution metrics
# ServiceToken contains the AWS account number which would remove the anonymous nature of the metrics
METRIC_DENYLIST_KEYS = ['ServiceToken']


def post_metrics(event):
    try:
        request_timestamp = str(datetime.datetime.utcnow().isoformat())
        solution_id = 'SO0280'
        uuid = event['RequestId']
        data = {
            'RequestType': event['RequestType'],
            'RequestTimeStamp': request_timestamp
        }

        # Need to validate where data is coming from
        for k, v in event['ResourceProperties'].items():
            if (
                k not in data.keys() and
                k not in METRIC_DENYLIST_KEYS
            ):
                data[k] = v
        # Metrics Account (Production)
        metrics_url = os.environ.get('AWS_METRICS_URL', 'https://metrics.awssolutionsbuilder.com/generic')

        time_stamp = {'TimeStamp': request_timestamp}
        params = {
            'Solution': solution_id,
            'UUID': uuid,
            'Data': data
        }

        metrics = dict(time_stamp, **params)
        json_data = json.dumps(metrics, indent=4)
        logger.info(params)
        headers = {'content-type': 'application/json'}
        req = http_client.http_post('POST',
                                    metrics_url,
                                    body=json_data.encode('utf-8'),
                                    headers=headers)
        rsp_code = req.status
        logger.info(f'ResponseCode: {rsp_code}')
    except Exception as e:
        logger.exception(f'failed to post metrics: {e}')


def handler(event, context):
    """
    To improve performance and usability, IDEA sends anonymous metrics to AWS.
    You can disable this by setting 'cluster.solution.enable_solution_metrics' to False with res-admin.sh
    Data tracked:
      - SOCA Instance information
      - SOCA Instance Count
      - SOCA Launch/Delete time
    """
    try:
        # Send Anonymous Metrics
        post_metrics(event)
    except Exception as e:
        logger.exception(f'failed to post metrics: {e}')
    finally:
        http_client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID
        ))
