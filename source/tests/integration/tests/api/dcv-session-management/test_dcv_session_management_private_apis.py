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

import pytest
import requests

from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


@pytest.mark.usefixtures("res_environment")
class TestDcvPrivateApi:
    """
    Verify that private DCV Session Management APIs served on the internal ALB
    are not accessible from the public network (outside the VPC).
    """

    def _internal_alb_url(self, res_environment: ResEnvironment, path: str) -> str:
        return f"https://{res_environment.internal_alb_endpoint}{path}"

    @pytest.mark.parametrize("method,path,kwargs", [
        ("get", "/health", {}),
        ("post", "/", {"json": {}}),
        ("post", "/sessionConnectionData/test-session/test-user", {}),
        ("post", "/describeSessions", {"json": {}}),
        ("post", "/sessionScreenshots", {"json": {}}),
        ("put", "/sessionPermissions", {"json": {}}),
        ("post", "/resolveSession", {"params": {"sessionId": "test", "transport": "tcp", "clientIpAddress": "127.0.0.1"}}),
    ])
    def test_private_api_not_accessible(self, res_environment: ResEnvironment, method: str, path: str, kwargs: dict) -> None:
        url = self._internal_alb_url(res_environment, path)
        logger.info(f"Verifying {url} is not reachable from public network")
        with pytest.raises(requests.exceptions.ConnectionError):
            getattr(requests, method)(url, timeout=REQUEST_TIMEOUT, verify=False, **kwargs)
