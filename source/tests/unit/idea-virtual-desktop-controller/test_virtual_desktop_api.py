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

import pytest
from ideavirtualdesktopcontroller.app.api.virtual_desktop_api import VirtualDesktopAPI

from ideadatamodel import VirtualDesktopSession, errorcodes, exceptions


def test_validate_get_session_info_request_success():
    """
    test validate get session info request, should succeed
    """
    virtualDesktopSession = VirtualDesktopSession(
        idea_session_id="00000000-0000-0000-0000-000000000000"
    )
    result = VirtualDesktopAPI.validate_get_session_info_request(virtualDesktopSession)
    assert result == True


def test_validate_get_session_info_request_empty_fail():
    """
    test validate get session info request with empty session id, should fail
    """
    virtualDesktopSession = VirtualDesktopSession()
    with pytest.raises(exceptions.SocaException) as exc_info:
        VirtualDesktopAPI.validate_get_session_info_request(virtualDesktopSession)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_validate_get_session_info_request_wrong_type_fail():
    """
    test validate get session info request with wrong session id type, should fail
    """
    virtualDesktopSession = VirtualDesktopSession(idea_session_id=0)
    with pytest.raises(exceptions.SocaException) as exc_info:
        VirtualDesktopAPI.validate_get_session_info_request(virtualDesktopSession)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_validate_get_session_info_request_invalid_uuid_fail():
    """
    test validate get session info request with invaid uuid, should fail
    """
    virtualDesktopSession = VirtualDesktopSession(idea_session_id="00000000")
    with pytest.raises(exceptions.SocaException) as exc_info:
        VirtualDesktopAPI.validate_get_session_info_request(virtualDesktopSession)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
