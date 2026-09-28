#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List

import pytest
from res.resources import sessions  # type: ignore

from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchGetSessionScreenshotRequestContent,
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
from tests.integration.framework.utils.model_utils import get_backend_model_class

VirtualDesktopSessionScreenshot = get_backend_model_class(
    "virtual_desktop_session_screenshot", "VirtualDesktopSessionScreenshot"
)
BatchOperationErrorCode = get_backend_model_class(
    "batch_operation_error_code", "BatchOperationErrorCode"
)

logger = logging.getLogger(__name__)


class TestBatchGetSessionScreenshot:

    def _build_request(self, session_records: List[Dict[str, Any]]) -> Any:
        """Build a BatchGetSessionScreenshotRequestContent from session records."""
        screenshots = [
            VirtualDesktopSessionScreenshot(
                idea_session_id=record[sessions.SESSION_DB_RANGE_KEY],
            )
            for record in session_records
        ]
        return BatchGetSessionScreenshotRequestContent(screenshots=screenshots)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-screenshot-admin-own",
                    sessions.SESSION_DB_HASH_KEY: "clusteradmin",
                    "state": "READY",
                },
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_with_admin_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Admin can request screenshots for their own session in dry-run mode."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_get_session_screenshot(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful screenshot"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-screenshot-admin-own"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful screenshots"

        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-screenshot-user1-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_get_session_screenshot_with_owner(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Non-admin can request screenshots for their own session."""
        set_backend_lambda_dry_mode(region, environment_name, True)
        try:
            api_client = ApiClient(res_environment, non_admin)
            request_content = self._build_request(session_record)
            response = api_client.batch_get_session_screenshot(request_content)

            assert response is not None, "Response should not be None"
            assert (
                len(response.successful_list) == 1
            ), "Should have 1 successful screenshot"
            assert (
                response.successful_list[0].idea_session_id
                == "test-batch-screenshot-user1-123"
            )
            assert (
                len(response.unsuccessful_list) == 0
            ), "There should be no unsuccessful screenshots"

            logger.info(
                "Non-admin user successfully requested screenshot for their own session"
            )
        finally:
            set_backend_lambda_dry_mode(region, environment_name, False)

    def test_batch_get_session_screenshot_with_nonexistent_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
    ) -> None:
        """Authenticating as a non-existent user is rejected with 401."""
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            screenshots = [
                VirtualDesktopSessionScreenshot(idea_session_id="test-session-123")
            ]
            request_content = BatchGetSessionScreenshotRequestContent(
                screenshots=screenshots
            )
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "User not found" in e.response.text
            ), f"Unexpected error for non-existent user: {str(e)}"

    @pytest.mark.parametrize("inactive_username", ["user2"])
    def test_batch_get_session_screenshot_with_inactive_user(
        self,
        region: str,
        res_environment: ResEnvironment,
        inactive_username: str,
        inactive_user: ClientAuth,
    ) -> None:
        """Inactive user authentication is rejected with 401."""
        try:
            api_client = ApiClient(res_environment, inactive_user)
            screenshots = [
                VirtualDesktopSessionScreenshot(idea_session_id="test-session-123")
            ]
            request_content = BatchGetSessionScreenshotRequestContent(
                screenshots=screenshots
            )
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected error for inactive user")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Inactive user" in e.response.text
            ), f"Unexpected error for inactive user: {str(e)}"

    def test_batch_get_session_screenshot_without_auth_token(
        self,
        res_environment: ResEnvironment,
        region: str,
    ) -> None:
        """Request without auth token is rejected with 401."""
        try:
            no_auth = ClientAuth(username="clusteradmin", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            screenshots = [
                VirtualDesktopSessionScreenshot(idea_session_id="test-session-123")
            ]
            request_content = BatchGetSessionScreenshotRequestContent(
                screenshots=screenshots
            )
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "No authorization token provided" in e.response.text
            ), f"Unexpected error for request without auth token: {str(e)}"

    def test_batch_get_session_screenshot_with_invalid_auth_token(
        self,
        region: str,
        res_environment: ResEnvironment,
        environment_name: str,
    ) -> None:
        """Invalid auth token is rejected with 401."""
        set_backend_lambda_test_mode(region, environment_name, False)
        try:
            invalid_auth = ClientAuth(
                username="clusteradmin", auth_token="invalid_token_12345"
            )
            api_client = ApiClient(res_environment, invalid_auth)
            screenshots = [
                VirtualDesktopSessionScreenshot(idea_session_id="test-session-123")
            ]
            request_content = BatchGetSessionScreenshotRequestContent(
                screenshots=screenshots
            )
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail(
                "Expected 'Unable to retrieve username' error for invalid auth token"
            )
        except Exception as e:
            assert "401" in str(e), f"Expected 401 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "Unable to retrieve username" in e.response.text
            ), f"Unexpected error for request with invalid auth token: {str(e)}"
        finally:
            set_backend_lambda_test_mode(region, environment_name, True)

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-screenshot-other-user-123",
                    sessions.SESSION_DB_HASH_KEY: "other_user",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    def test_batch_get_session_screenshot_non_admin_other_users_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        non_admin_username: str,
        non_admin: ClientAuth,
    ) -> None:
        """Non-admin requesting another user's session screenshot gets FORBIDDEN
        from the private DCV API's session-permissions check."""
        api_client = ApiClient(res_environment, non_admin)
        request_content = self._build_request(session_record)
        response = api_client.batch_get_session_screenshot(request_content)

        assert response is not None, "Response should not be None"
        assert (
            len(response.successful_list) == 0
        ), "Should have no successful screenshots"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful screenshot"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.FORBIDDENEXCEPTION
        ), "Error code should be ForbiddenException"

        logger.info(
            "Non-admin correctly received ForbiddenException for other user's session"
        )

    @pytest.mark.parametrize(
        "session_record",
        [
            [
                {
                    "session_id": "test-batch-screenshot-admin-other-user-123",
                    sessions.SESSION_DB_HASH_KEY: "user1",
                    "state": "READY",
                }
            ]
        ],
        indirect=True,
    )
    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_admin_other_users_session(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        session_record: List[Dict[str, Any]],
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Admin status grants no bypass: an admin without ownership or shared
        session permission still gets FORBIDDEN from the private DCV API."""
        api_client = ApiClient(res_environment, admin)
        request_content = self._build_request(session_record)
        response = api_client.batch_get_session_screenshot(request_content)

        assert response is not None, "Response should not be None"
        assert (
            len(response.successful_list) == 0
        ), "Should have no successful screenshots"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful screenshot"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.FORBIDDENEXCEPTION
        ), "Error code should be ForbiddenException"

        logger.info(
            "Admin correctly received ForbiddenException for other user's session (no admin bypass)"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_nonexistent_session(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """A session that does not exist in DDB returns FORBIDDEN from the private
        API (validate_session_access raises SessionAccessDenied with the same message
        whether the session is missing or unauthorized)."""
        api_client = ApiClient(res_environment, admin)
        screenshots = [
            VirtualDesktopSessionScreenshot(idea_session_id="nonexistent-session-999")
        ]
        request_content = BatchGetSessionScreenshotRequestContent(
            screenshots=screenshots
        )
        response = api_client.batch_get_session_screenshot(request_content)

        assert response is not None, "Response should not be None"
        assert (
            len(response.successful_list) == 0
        ), "Should have no successful screenshots"
        assert (
            len(response.unsuccessful_list) == 1
        ), "Should have 1 unsuccessful screenshot"
        assert (
            response.unsuccessful_list[0].error_code
            == BatchOperationErrorCode.FORBIDDENEXCEPTION
        ), f"Expected FORBIDDEN, got: {response.unsuccessful_list[0].error_code}"

        logger.info(
            f"Non-existent session correctly returned in unsuccessful list: "
            f"{response.unsuccessful_list[0].message}"
        )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_empty_screenshots_list(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """An empty screenshots list is rejected with 400 by connexion"""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchGetSessionScreenshotRequestContent(screenshots=[])
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected 400 error for empty screenshots list")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "[] should be non-empty - 'screenshots'" in e.response.text
            ), f"Unexpected error for empty screenshots list: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_missing_screenshots_field(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """Missing screenshots field returns 400."""
        try:
            api_client = ApiClient(res_environment, admin)
            request_content = BatchGetSessionScreenshotRequestContent(screenshots=None)
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected 400 error for missing screenshots field")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "'screenshots' is a required property" in e.response.text
            ), f"Unexpected error for missing screenshots field: {e.response.text}"

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_batch_get_session_screenshot_missing_idea_session_id(
        self,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        """A screenshot entry without idea_session_id is rejected with 400 by connexion."""
        try:
            api_client = ApiClient(res_environment, admin)
            screenshots = [VirtualDesktopSessionScreenshot()]
            request_content = BatchGetSessionScreenshotRequestContent(
                screenshots=screenshots
            )
            api_client.batch_get_session_screenshot(request_content)
            pytest.fail("Expected 400 error for missing idea_session_id")
        except Exception as e:
            assert "400" in str(e), f"Expected 400 error, got: {str(e)}"
            assert hasattr(e, "response"), "Response should exist in the exception"
            assert (
                "'idea_session_id' is a required property" in e.response.text
            ), f"Unexpected error for missing idea_session_id: {e.response.text}"
