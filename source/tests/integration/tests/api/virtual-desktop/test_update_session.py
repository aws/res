#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import pytest

from tests.integration.framework.client.api_client import (
    ApiClient,
    UpdateSessionRequestContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, non_admin
from tests.integration.framework.model.client_auth import ClientAuth

logger = logging.getLogger(__name__)


class TestUpdateSession:

    def _get_update_session_payload(self, session_id: str, **overrides):  # type: ignore
        """Helper method to create update session request payload."""
        payload = {
            "session": {
                "idea_session_id": session_id,
                "owner": "clusteradmin",
                "name": "UpdatedDesktopSession",
                "description": "Updated description",
                "hibernation_enabled": False,
                "server": {"instance_type": "m6a.xlarge"},
            }
        }
        if overrides:
            payload["session"].update(overrides)
        return payload

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_request_with_dry_mode_as_admin(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that admin can successfully update session in dry run mode."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_dry_mode,
        )

        set_backend_lambda_dry_mode(region, environment_name, True)
        api_client = ApiClient(res_environment, admin)

        try:
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id)
            response = api_client.update_session(
                session_id, UpdateSessionRequestContent(**payload)
            )

            assert response is not None
            assert hasattr(
                response, "session"
            ), "Response should have session attribute"
            session = response.session
            assert session is not None, "Session should not be None"
            # In dry run mode, the session should echo back the input values
            assert (
                session.name == payload["session"]["name"]
            ), "Session name should match input"
            assert (
                session.description == payload["session"]["description"]
            ), "Description should match input"

            logger.info("Admin successfully updated session in dry run mode")
        except Exception as e:
            pytest.fail(f"Unexpected API error while updating session: {str(e)}")
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_missing_session(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that update session fails when session payload is missing."""
        api_client = ApiClient(res_environment, admin)

        try:
            # Create empty payload without session
            payload: Any = {}
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session("dummy-session-id", request_content)
            pytest.fail("Expected 400 error for missing session")
        except Exception as e:
            assert "400" in str(e)
            assert hasattr(e, "response")
            assert hasattr(e.response, "text")
            assert "'session' is a required property" in e.response.text

    def test_update_session_with_nonexistent_user_returns_user_not_found_error(
        self, res_environment: ResEnvironment
    ) -> None:
        """Test that non-existent users get proper 'User not found' error for update session endpoint."""
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id)
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session(session_id, request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "User not found" in response_content:
                    logger.info(
                        "Non-existent user correctly received 'User not found' error for update session endpoint"
                    )
                    return

            pytest.fail(f"Unexpected error for non-existent user: {str(e)}")

    def test_update_session_without_auth_token_returns_no_authorization_token_provided_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """Test that requests without auth tokens get proper 'No authorization token provided' error for update session endpoint."""
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id)
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session(session_id, request_content)
            pytest.fail(
                "Expected 'No authorization token provided' error for request without auth token"
            )
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "No authorization token provided" in response_content:
                    logger.info(
                        "Request without auth token correctly received 'No authorization token provided' error for update session endpoint"
                    )
                    return

            pytest.fail(f"Unexpected error for request without auth token: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_in_prod_with_invalid_auth_token_returns_unable_to_retrieve_username_error(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        admin: ClientAuth,
    ) -> None:
        """Test that requests with invalid auth tokens get proper error in production for update session endpoint."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_test_mode,
        )

        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            api_client = ApiClient(res_environment, admin)
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id)
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session(session_id, request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for request with invalid auth token"
            )
        except Exception as e:
            if "401" in str(e):
                assert hasattr(e, "response"), "Response should exist in the exception"
                assert e.response is not None, "Response should not be None"

                response_content = e.response.text
                if "Unable to retrieve username" in response_content:
                    logger.info(
                        "Request with invalid auth token correctly received 'Unable to retrieve username' error for update session endpoint"
                    )
                    return

            pytest.fail(
                f"Unexpected error for request with invalid auth token: {str(e)}"
            )
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_update_session_request_with_dry_mode_as_non_admin(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user can successfully update session in dry run mode."""
        from tests.integration.framework.utils.lambda_utils import (
            set_backend_lambda_dry_mode,
        )

        set_backend_lambda_dry_mode(region, environment_name, True)
        api_client = ApiClient(res_environment, non_admin)

        try:
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id, owner="user1")
            response = api_client.update_session(
                session_id, UpdateSessionRequestContent(**payload)
            )

            assert response is not None
            assert hasattr(
                response, "session"
            ), "Response should have session attribute"
            session = response.session
            assert session is not None, "Session should not be None"
            assert (
                session.name == payload["session"]["name"]
            ), "Session name should match input"
            logger.info("Non-admin user successfully updated session in dry run mode")
        except Exception as e:
            pytest.fail(
                f"Unexpected API error while updating session as non-admin: {str(e)}"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_update_session_as_non_admin_for_other_user_fails(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Test that non-admin user cannot update another user's session."""
        api_client = ApiClient(res_environment, non_admin)

        try:
            session_id = "81fb4fd4-e065-46e9-a7f9-e124dc4e7148"
            payload = self._get_update_session_payload(session_id, owner="clusteradmin")
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session(session_id, request_content)
            pytest.fail("Expected error for non-admin updating another user's session")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            logger.info(
                "Non-admin correctly denied from updating another user's session"
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_session_nonexistent_session_fails(
        self,
        request: FixtureRequest,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Test that updating a non-existent session returns proper error."""
        api_client = ApiClient(res_environment, admin)

        try:
            session_id = "nonexistent-session-id-12345"
            payload = self._get_update_session_payload(session_id)
            request_content = UpdateSessionRequestContent(**payload)

            api_client.update_session(session_id, request_content)
            pytest.fail("Expected error for non-existent session")
        except Exception as e:
            assert "400" in str(e) or "does not exist" in str(
                e
            ), f"Expected 400 error, got: {str(e)}"
            logger.info("Non-existent session correctly returned error")
