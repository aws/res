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

from typing import List, Optional

import pytest
from ideasdk.api import ApiInvocationContext, BaseAPI
from ideasdk.client import SocaClient, SocaClientOptions
from ideasdk.context import SocaContext, SocaContextOptions
from ideasdk.protocols import (
    ApiAuthorizationServiceProtocol,
    ApiInvokerProtocol,
    TokenServiceProtocol,
)
from ideasdk.server import SocaServer, SocaServerOptions
from ideasdk.utils import Utils
from ideatestutils import MockConfig

from ideadatamodel import (
    SocaBaseModel,
    SocaListingPayload,
    SocaPayload,
    errorcodes,
    exceptions,
)

HOST_IP = "127.0.0.1"
SERVER_PORT = 34567
UNIX_SOCKET_FILE = "/tmp/soca/test_socket.sock"


# Create sample Calculator API Data Model


class CalculateRequest(SocaPayload):
    num1: Optional[int]
    num2: Optional[int]


class CalculateResult(SocaPayload):
    result: Optional[int]


class CalculateHistoryEntry(SocaBaseModel):
    num1: Optional[int]
    num2: Optional[int]
    operation: Optional[str]
    result: Optional[int]


class ListHistoryRequest(SocaListingPayload):
    pass


class ListHistoryResult(SocaListingPayload):
    listing: Optional[List[CalculateHistoryEntry]]


# Create Calculator API


class CalculatorAPI(BaseAPI):
    def __init__(self):
        self._history = []

    def add_to_history(self, entry: CalculateHistoryEntry):
        if len(self._history) > 100:
            self._history.pop(0)
        self._history.append(entry)

    def add(self, context: ApiInvocationContext):
        payload = context.get_request_payload_as(CalculateRequest)
        num1 = Utils.get_as_int(payload.num1, 0)
        num2 = Utils.get_as_int(payload.num2, 0)
        result = num1 + num2
        self._history.append(CalculateHistoryEntry(num1=num1, num2=num2, result=result))
        context.success(CalculateResult(result=result))

    def multiply(self, context: ApiInvocationContext):
        payload = context.get_request_payload_as(CalculateRequest)
        num1 = Utils.get_as_int(payload.num1, 0)
        num2 = Utils.get_as_int(payload.num2, 0)
        result = num1 * num2
        self._history.append(CalculateHistoryEntry(num1=num1, num2=num2, result=result))
        context.success(CalculateResult(result=result))

    def divide(self, context: ApiInvocationContext):
        payload = context.get_request_payload_as(CalculateRequest)
        num1 = Utils.get_as_int(payload.num1, 0)
        num2 = Utils.get_as_int(payload.num2, 0)

        if num2 == 0:
            raise exceptions.invalid_params("num2 cannot be zero")

        result = int(num1 / num2)

        self._history.append(CalculateHistoryEntry(num1=num1, num2=num2, result=result))
        context.success(CalculateResult(result=result))

    def subtract(self, context: ApiInvocationContext):
        payload = context.get_request_payload_as(CalculateRequest)
        num1 = Utils.get_as_int(payload.num1, 0)
        num2 = Utils.get_as_int(payload.num2, 0)
        result = num1 - num2
        self._history.append(CalculateHistoryEntry(num1=num1, num2=num2, result=result))
        context.success(CalculateResult(result=result))

    def list_history(self, context: ApiInvocationContext):
        context.success(ListHistoryResult(listing=self._history))

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        if namespace == "Calculator.Add":
            self.add(context)
        elif namespace == "Calculator.Multiply":
            self.multiply(context)
        elif namespace == "Calculator.Divide":
            self.divide(context)
        elif namespace == "Calculator.Subtract":
            self.subtract(context)
        elif namespace == "Calculator.ListHistory":
            self.list_history(context)


# Create Calculator API Invoker
class ApiInvoker(ApiInvokerProtocol):
    def __init__(self):
        self.calculator_api = CalculatorAPI()

    def get_token_service(self) -> Optional[TokenServiceProtocol]:
        return None

    def get_api_authorization_service(
        self,
    ) -> Optional[ApiAuthorizationServiceProtocol]:
        return None

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        if namespace.startswith("Calculator."):
            self.calculator_api.invoke(context)


@pytest.fixture(scope="session")
def context():
    mock_config = MockConfig()
    return SocaContext(
        options=SocaContextOptions(
            module_id="test-server",
            module_name="test-server",
            config=mock_config.get_config(),
        )
    )


@pytest.fixture(scope="session", autouse=True)
def server(context):
    # Initialize SocaServer: HTTP + UNIX Socket
    server = SocaServer(
        context=context,
        api_invoker=ApiInvoker(),
        options=SocaServerOptions(
            enable_http=True,
            hostname=HOST_IP,
            port=SERVER_PORT,
            enable_unix_socket=True,
            unix_socket_file=UNIX_SOCKET_FILE,
            graceful_shutdown_timeout=1,
            enable_openapi_spec=False,
            api_path_prefixes=["/test-server"],
        ),
    )
    server.initialize()
    server.start()

    yield server

    server.stop()
    assert Utils.is_socket(UNIX_SOCKET_FILE) is False


@pytest.fixture(scope="session")
def http_client(context):
    return SocaClient(
        context=context,
        options=SocaClientOptions(
            enable_logging=True,
            endpoint=f"http://localhost:{SERVER_PORT}/test-server/api/v1",
        ),
    )


@pytest.fixture(scope="session")
def unix_client(context):
    return SocaClient(
        context=context,
        options=SocaClientOptions(
            enable_logging=True,
            endpoint="http://localhost/test-server/api/v1",
            unix_socket=UNIX_SOCKET_FILE,
        ),
    )


@pytest.fixture(scope="session")
def logger(context):
    return context.logger()


def invoke(
    http_client,
    unix_client,
    logger,
    namespace: str,
    num1: int,
    num2: int,
    assert_result: int,
):
    logger.info("http")
    result = http_client.invoke_alt(
        namespace,
        payload=CalculateRequest(num1=num1, num2=num2),
        result_as=CalculateResult,
    )
    assert result.result == assert_result

    logger.info("unix socket")
    result = unix_client.invoke_alt(
        namespace,
        payload=CalculateRequest(num1=num1, num2=num2),
        result_as=CalculateResult,
    )
    assert result.result == assert_result


def invoke_listing(http_client, unix_client, logger, namespace: str, result_count: int):
    logger.info("http")
    result = http_client.invoke_alt(
        namespace, payload=ListHistoryRequest(), result_as=ListHistoryResult
    )
    assert len(result.listing) == result_count

    logger.info("unix socket")
    result = unix_client.invoke_alt(
        namespace, payload=ListHistoryRequest(), result_as=ListHistoryResult
    )
    assert len(result.listing) == result_count

    # verify deserialization for listing results
    first = result.listing[0]
    assert first.num1 is not None
    assert first.num2 is not None
    assert first.result is not None


def test_server(monkeypatch, http_client, unix_client, logger):
    invoke(http_client, unix_client, logger, "Calculator.Add", 10, 20, 30)
    invoke(http_client, unix_client, logger, "Calculator.Subtract", 20, 10, 10)
    invoke(http_client, unix_client, logger, "Calculator.Multiply", 20, 10, 200)
    invoke(http_client, unix_client, logger, "Calculator.Divide", 20, 10, 2)
    invoke_listing(http_client, unix_client, logger, "Calculator.ListHistory", 8)

    # test any payload (with SimpleNamespace)
    result = http_client.invoke_alt(
        namespace="Calculator.Add", payload=CalculateRequest(num1=10, num2=20)
    )
    assert result.result == 30

    # test exception
    with pytest.raises(exceptions.SocaException) as divide_by_zero:
        http_client.invoke_alt(
            namespace="Calculator.Divide", payload=CalculateRequest(num1=10, num2=0)
        )
    assert divide_by_zero.value.error_code == errorcodes.INVALID_PARAMS

    assert Utils.is_socket(UNIX_SOCKET_FILE) is True
