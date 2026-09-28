#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Optional

import pytest
from res.resources import sessions  # type: ignore
from res.utils.model_utils import remove_none_values  # type: ignore

from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackFromSessionRequestContent,
    CreateSoftwareStackFromSessionResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session_record import session_record
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.lambda_utils import (
    set_backend_lambda_dry_mode,
    set_backend_lambda_test_mode,
)

logger = logging.getLogger(__name__)

VALID_SESSION = {
    "idea_session_id": "test-session-123",
    "owner": "clusteradmin",
}


@pytest.fixture
def default_software_stack(res_environment: ResEnvironment) -> Dict[str, Any]:
    """Fetch a real default software stack from the environment."""
    client_auth = ClientAuth(username="clusteradmin")
    api_client = ApiClient(res_environment, client_auth)
    response = api_client.list_software_stacks()
    for stack in response.listing or []:  # type: ignore[attr-defined]
        if stack.ami_id and stack.base_os:
            return remove_none_values(stack.to_dict())  # type: ignore[no-any-return]
    pytest.skip("No software stack with ami_id found in environment")


def _build_valid_raw_request(
    software_stack: Dict[str, Any],
    session_overrides: Optional[Dict[str, Any]] = None,
    stack_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a raw request dict with all required fields, applying overrides."""
    session_dict = {**VALID_SESSION, **(session_overrides or {})}
    stack_dict = {**software_stack, **(stack_overrides or {})}
    return {"session": session_dict, "software_stack": stack_dict}


def _build_request(
    software_stack: Dict[str, Any],
    idea_session_id: str,
    owner: str,
    stack_name: Optional[str] = None,
) -> CreateSoftwareStackFromSessionRequestContent:
    stack = {**software_stack}
    stack.pop("stack_id", None)
    if stack_name:
        stack["name"] = stack_name
    return CreateSoftwareStackFromSessionRequestContent(
        session={"idea_session_id": idea_session_id, "owner": owner},
        software_stack=stack,
    )


class TestCreateSoftwareStackFromSession:

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-stack-from-sess-003",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                    "software_stack": {"base_os": "amazonlinux2"},
                    "server": {"instance_id": "i-00000000000000000"},
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_with_valid_request(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            record = session_record[0]
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
                stack_name="integ-test-stack-from-session",
            )
            response = api_client.create_software_stack_from_session(request_content)

            assert response is not None, "Response should not be None"
            assert (
                response.software_stack is not None
            ), "Response must contain software_stack"
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_empty_body(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.create_software_stack_from_session({}, raw=True)
            pytest.fail("Expected 400 error for empty body")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_missing_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.create_software_stack_from_session(
                {"software_stack": default_software_stack},
                raw=True,
            )
            pytest.fail("Expected 400 error for missing session")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "'session' is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_missing_software_stack(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            api_client.create_software_stack_from_session(
                {"session": VALID_SESSION},
                raw=True,
            )
            pytest.fail("Expected 400 error for missing software_stack")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "'software_stack' is a required property" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_missing_session_owner(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request = _build_valid_raw_request(software_stack=default_software_stack)
            request["session"]["owner"] = ""
            api_client.create_software_stack_from_session(request, raw=True)
            pytest.fail("Expected 400 error for missing session.owner")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "session.owner is required" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_missing_session_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request = _build_valid_raw_request(software_stack=default_software_stack)
            request["session"]["idea_session_id"] = ""
            api_client.create_software_stack_from_session(request, raw=True)
            pytest.fail("Expected 400 error for missing session.idea_session_id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "session.idea_session_id is required" in e.response.text

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="nonexistent-session-xyz",
                owner="clusteradmin",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 400 error for non-existent session")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert (
                "Session nonexistent-session-xyz not found for owner clusteradmin"
                in e.response.text
            )

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-stack-from-sess-001",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                    "software_stack": {"base_os": "amazonlinux2"},
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_missing_stack_name(
        self,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        record = session_record[0]
        try:
            api_client = ApiClient(res_environment, admin)
            stack = {**default_software_stack}
            del stack["name"]
            api_client.create_software_stack_from_session(
                {
                    "session": {
                        "idea_session_id": record[sessions.SESSION_DB_RANGE_KEY],
                        "owner": record[sessions.SESSION_DB_HASH_KEY],
                    },
                    "software_stack": stack,
                },
                raw=True,
            )
            pytest.fail("Expected 400 error for missing software_stack.name")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "'name' is a required property - 'software_stack'" in e.response.text

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-stack-from-sess-002",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                    "software_stack": {"base_os": "amazonlinux2"},
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_duplicate_ami_name(
        self,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        """Use the name of an existing software stack so validation rejects it."""
        record = session_record[0]
        try:
            api_client = ApiClient(res_environment, admin)
            # Use the default stack's own name — guaranteed to exist in DDB
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
                stack_name=default_software_stack["name"],
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 400 error for duplicate stack name")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "already exists" in e.response.text

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_create_software_stack_from_session_with_non_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="test-session-123",
                owner="user1",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 401 error for non-admin user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_create_software_stack_from_session_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            api_client = ApiClient(res_environment, inactive_user)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="test-session-123",
                owner="user2",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 401 error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Expected 'Inactive user' in response, got: {e.response.text}"

    def test_create_software_stack_from_session_with_nonexistent_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="test-session-123",
                owner="nonexistent_user_12345",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 401 error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Expected 'User not found' in response, got: {e.response.text}"

    def test_create_software_stack_from_session_without_auth_token(
        self,
        region: str,
        res_environment: ResEnvironment,
        default_software_stack: Dict[str, Any],
    ) -> None:
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="test-session-123",
                owner="clusteradmin",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 401 error for missing auth token")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "No authorization token provided" in e.response.text

    def test_create_software_stack_from_session_with_invalid_auth_token_in_prod(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        default_software_stack: Dict[str, Any],
    ) -> None:
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id="test-session-123",
                owner="clusteradmin",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 401 error for invalid auth token")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "Unable to retrieve username" in e.response.text
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_with_empty_name(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Verify that an empty software stack name is rejected by @length(min: 1) validation."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = CreateSoftwareStackFromSessionRequestContent(
                session={"idea_session_id": "fake-session-id", "owner": "clusteradmin"},
                software_stack={
                    "name": "",
                    "base_os": "amzn2023",
                    "ami_id": "ami-fake",
                    "gpu": "NO_GPU",
                    "min_storage": {"value": 100, "unit": "gb"},
                    "min_ram": {"value": 22, "unit": "gb"},
                },
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 400 error for empty software stack name")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert e.response.status_code == 400
            assert "should be non-empty" in e.response.text

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-stack-from-sess-non-ready",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "STOPPED",
                    "software_stack": {"base_os": "amazonlinux2"},
                    "server": {"instance_id": "i-00000000000000000"},
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_create_software_stack_from_session_non_ready_session_rejected(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
        default_software_stack: Dict[str, Any],
    ) -> None:
        """Verify that a session not in READY state returns 400 with a clear message."""
        record = session_record[0]
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = _build_request(
                software_stack=default_software_stack,
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
                owner=record[sessions.SESSION_DB_HASH_KEY],
                stack_name="integ-test-non-ready-session",
            )
            api_client.create_software_stack_from_session(request_content)
            pytest.fail("Expected 400 error for non-READY session")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response")
            assert "READY" in e.response.text
            assert "STOPPED" in e.response.text
