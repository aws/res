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

"""
Test Cases for ApiInvocationContext
"""

from typing import Dict

import pytest
from ideasdk.api import ApiInvocationContext
from ideasdk.auth import TokenService
from ideasdk.context import SocaContext, SocaContextOptions
from ideasdk.utils import GroupNameHelper, Utils
from ideatestutils.config.mock_config import MockConfig

from ideadatamodel import constants, errorcodes, exceptions


@pytest.fixture(scope="session")
def context():
    mock_config = MockConfig()
    return SocaContext(options=SocaContextOptions(config=mock_config.get_config()))


def build_invocation_context(
    context: SocaContext,
    payload: Dict,
    invocation_source: str = None,
    token: Dict = None,
    token_service: TokenService = None,
) -> ApiInvocationContext:
    if Utils.is_empty(invocation_source):
        invocation_source = constants.API_INVOCATION_SOURCE_HTTP

    return ApiInvocationContext(
        context=context,
        request=payload,
        invocation_source=invocation_source,
        group_name_helper=GroupNameHelper(context=context),
        logger=context.logger(),
        token=token,
        token_service=token_service,
    )


def test_api_invocation_context_validate_request_valid(context):
    """
    validate request - valid request
    """
    api_context = build_invocation_context(
        context=context,
        payload={
            "header": {"namespace": "Hello.World", "request_id": Utils.uuid()},
            "payload": {},
        },
    )

    # should not raise any exceptions
    api_context.validate_request()


def test_api_invocation_context_validate_request_invalid(context):
    """
    validate request - invalid request, namespace contains special characters
    """
    api_context = build_invocation_context(
        context=context,
        payload={
            "header": {"namespace": "Hello.\n\nWorld", "request_id": Utils.uuid()},
            "payload": {},
        },
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        api_context.validate_request()
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
