#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, TypedDict
from urllib.request import Request, urlopen


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str
    Data: Dict[str, Any]


def send_response(url: str, response: CustomResourceResponse) -> None:
    request = Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urlopen(request)
