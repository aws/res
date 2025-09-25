#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import datetime
import json
import logging
import os
from typing import Any, Dict

import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HTTP_CLIENT = urllib3.PoolManager()

# Metric Keys that come in to the Lambda that are not relayed to the IDEA solution metrics
# ServiceToken contains the AWS account number which would remove the anonymous nature of the metrics
METRIC_DENYLIST_KEYS = ["ServiceToken"]


def post_metrics(event: Dict[str, Any]) -> None:
    try:
        request_timestamp = str(datetime.datetime.utcnow().isoformat())
        solution_id = "SO0280"
        uuid = event["RequestId"]
        data = {
            "RequestType": event["RequestType"],
            "RequestTimeStamp": request_timestamp,
        }

        # Need to validate where data is coming from
        for k, v in event["ResourceProperties"].items():
            if k not in data.keys() and k not in METRIC_DENYLIST_KEYS:
                data[k] = v
        # Metrics Account (Production)
        metrics_url = os.environ.get(
            "AWS_METRICS_URL", "https://metrics.awssolutionsbuilder.com/generic"
        )

        time_stamp = {"TimeStamp": request_timestamp}
        params = {"Solution": solution_id, "UUID": uuid, "Data": data}

        metrics = dict(time_stamp, **params)
        json_data = json.dumps(metrics, indent=4)
        logger.info(params)
        headers = {"content-type": "application/json"}
        req = HTTP_CLIENT.request(  # type: ignore
            "POST", metrics_url, body=json_data.encode("utf-8"), headers=headers
        )
        rsp_code = req.status
        logger.info(f"ResponseCode: {rsp_code}")
    except Exception as e:
        logger.exception(f"failed to post metrics: {e}")


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
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
        error_message = f"failed to post metrics: {e}"

        raise Exception(error_message)
