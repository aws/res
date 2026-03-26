import html
import logging
import uuid
from typing import Any, Dict

import pytest

from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSoftwareStackRequestContent,
    CreateSoftwareStackResponseContent,
    DeleteSoftwareStackRequestContent,
    UpdateSoftwareStackRequestContent,
    UpdateSoftwareStackResponseContent,
)
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.users import admin, inactive_user, non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.virtual_desktop import (
    get_software_stack_base_payload,
)

logger = logging.getLogger(__name__)


class TestUpdateSoftwareStack:

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_software_stack_with_valid_request(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            software_stack_name = f"basic-software-stack-valid-request"
            payload: Dict[str, Any] = get_software_stack_base_payload(
                region, name=software_stack_name
            )
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )

            try:

                assert response is not None
                assert hasattr(response, "software_stack")
                assert response.software_stack is not None
                assert response.software_stack.version is 1
                assert response.software_stack.stack_id is not None
                assert response.software_stack.base_os is not None

                updated_name = "software-stack-update-valid"
                updated_description = "New description"

                update_payload = response.software_stack.to_dict()
                update_payload["name"] = updated_name
                update_payload["description"] = updated_description
                update_payload["min_storage"] = {"value": 122, "unit": "gb"}
                update_payload["min_ram"] = {"value": 55, "unit": "gb"}
                # Ensure base_os is included in update payload
                update_payload["base_os"] = response.software_stack.base_os

                update_request = UpdateSoftwareStackRequestContent(
                    software_stack=update_payload
                )

                update_response: UpdateSoftwareStackResponseContent = (
                    api_client.update_software_stack(
                        response.software_stack.stack_id, update_request
                    )
                )

                # Assert updated values
                assert update_response.software_stack.name == updated_name
                assert update_response.software_stack.description == updated_description
                assert update_response.software_stack.min_storage.value == 122
                assert update_response.software_stack.min_storage.unit == "gb"
                assert update_response.software_stack.min_ram.value == 55
                assert update_response.software_stack.min_ram.unit == "gb"
                assert update_response.software_stack.version == 2

                delete_request = DeleteSoftwareStackRequestContent(
                    base_os=payload["software_stack"]["base_os"]
                )
                api_client.delete_software_stack(
                    update_response.software_stack.stack_id, delete_request
                )
            except Exception as e:
                pytest.fail(
                    f"Unexpected API error while updating softwarestack: {str(e)}"
                )
        except Exception as e:
            pytest.fail(f"Unexpected API error creating software stack: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_software_stack_with_incorrect_stack_id(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            api_client = ApiClient(res_environment, admin)
            # Use unique name to avoid conflicts
            software_stack_name = f"basic-software-stack-incorrect-stack-id"
            payload: Dict[str, Any] = get_software_stack_base_payload(
                region, name=software_stack_name
            )
            request_content = CreateSoftwareStackRequestContent(**payload)
            response: CreateSoftwareStackResponseContent = (
                api_client.create_software_stack(request_content)
            )

            try:
                assert response is not None
                assert hasattr(response, "software_stack")
                assert response.software_stack is not None

                update_payload = response.software_stack.to_dict()
                del update_payload["stack_id"]
                update_payload["name"] = "software-stack-update-stack-id"
                update_payload["description"] = "New description"
                update_payload["min_storage"] = {"value": 122, "unit": "gb"}
                update_payload["min_ram"] = {"value": 55, "unit": "gb"}
                # Ensure base_os is included in update payload
                update_payload["base_os"] = payload["software_stack"]["base_os"]

                update_request = UpdateSoftwareStackRequestContent(
                    software_stack=update_payload
                )

                api_client.update_software_stack("fake-stack-id-1234", update_request)
                pytest.fail("Expected 404 error for invalid stack_id")
            except Exception as e:
                error_str = str(e)
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    response_content = e.response.text
                    assert (
                        "Software stack with" in response_content
                        and "not found" in response_content
                    )
                assert "404" in error_str
                delete_request = DeleteSoftwareStackRequestContent(
                    base_os=payload["software_stack"]["base_os"]
                )
                api_client.delete_software_stack(
                    response.software_stack.stack_id, delete_request
                )
        except Exception as e:
            pytest.fail(f"Unexpected API error creating software stack: {str(e)}")

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_software_stack_with_incorrect_base_os(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        api_client = ApiClient(res_environment, admin)
        # Use unique name to avoid conflicts
        software_stack_name = f"basic-software-stack-incorrect-base-os"
        payload: Dict[str, Any] = get_software_stack_base_payload(
            region, name=software_stack_name
        )
        request_content = CreateSoftwareStackRequestContent(**payload)
        response: CreateSoftwareStackResponseContent = api_client.create_software_stack(
            request_content
        )

        assert response is not None
        assert hasattr(response, "software_stack")
        assert response.software_stack is not None

        update_payload = response.software_stack.to_dict()
        del update_payload["stack_id"]
        update_payload["base_os"] = "fake-os"
        update_payload["name"] = "software-stack-update"
        update_payload["description"] = "New description"

        update_request = UpdateSoftwareStackRequestContent(
            software_stack=update_payload
        )

        try:
            api_client.update_software_stack(
                response.software_stack.stack_id, update_request
            )
            pytest.fail("Expected 400 error for invalid base_os")
        except Exception as e:
            # Check if it's a requests HTTPError with response content
            if hasattr(e, "response") and hasattr(e.response, "text"):
                error_str = e.response.text
            else:
                error_str = str(e)
            assert (
                "fake-os" in error_str
                and "400" in error_str
                and "is not one of" in error_str
                and "software_stack.base_os" in error_str
            )
        finally:
            # Always clean up the created software stack
            delete_request = DeleteSoftwareStackRequestContent(
                base_os=payload["software_stack"]["base_os"]
            )
            api_client.delete_software_stack(
                response.software_stack.stack_id, delete_request
            )

    @pytest.mark.parametrize("admin_username", ["clusteradmin"])
    def test_update_software_stack_invalid_user(
        self,
        request: FixtureRequest,
        region: str,
        res_environment: ResEnvironment,
        admin_username: str,
        admin: ClientAuth,
    ) -> None:
        try:
            nonexistent_auth = ClientAuth(username="nonexistent_user_12345")
            api_client = ApiClient(res_environment, nonexistent_auth)
            payload = get_software_stack_base_payload(region)
            update_request = UpdateSoftwareStackRequestContent(**payload)
            api_client.update_software_stack("12345-test", update_request)
            pytest.fail("Expected 'User not found' error for non-existent user")
        except Exception as e:
            assert "401" in str(e)
            logger.info(f"Non-existent user correctly received error: {str(e)}")

    def test_update_software_stack_without_auth_token(
        self, res_environment: ResEnvironment, region: str
    ) -> None:
        try:
            no_auth = ClientAuth(username="user1", auth_token=None)
            api_client = ApiClient(res_environment, no_auth)
            payload = get_software_stack_base_payload(region)
            request_content = UpdateSoftwareStackRequestContent(**payload)
            api_client.update_software_stack("fake-stack-id-1234", request_content)
            pytest.fail("Expected 'No authorization token provided' error")
        except Exception as e:
            assert "401" in str(e)
            logger.info(
                f"Request without auth token correctly received error: {str(e)}"
            )
