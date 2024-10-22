#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import http
import json
import os
import re
import sys
import typing
import urllib.parse
from datetime import datetime
from http.client import HTTPResponse
from typing import Any, Dict, List

import boto3
import botocore
from botocore.client import BaseClient
from dateutil.tz import tzlocal

# Lambda layers are copied over to "/opt", import those to sys.path
if not os.path.exists("/opt"):
    raise Exception("Lambda layer not found")
sys.path.insert(0, "/opt")

# Now you can import the modules from the Lambda layer
import jwt
from jwt import PyJWKClient

DEFAULT_JWK_CACHE_KEYS = True
DEFAULT_JWK_MAX_CACHED_KEYS = 16
DEFAULT_KEY_ALGORITHM = "RS256"
ADMIN_ROLE = "admin"


def get_signing_key(jwt_token: str) -> Any:
    jwk_client = PyJWKClient(
        uri=f'{os.environ["COGNITO_USER_POOL_PROVIDER_URL"]}/.well-known/jwks.json',
        cache_keys=DEFAULT_JWK_CACHE_KEYS,
        max_cached_keys=DEFAULT_JWK_MAX_CACHED_KEYS,
    )

    return jwk_client.get_signing_key_from_jwt(jwt_token).key


def decode_jwt(jwt_token: str) -> Dict[str, Any]:
    decoded_token = jwt.decode(
        jwt_token,
        get_signing_key(jwt_token),
        algorithms=[DEFAULT_KEY_ALGORITHM],
        options={"verify_exp": True},
    )
    if not isinstance(decoded_token, dict):
        raise Exception("Unexpected type of decoded token")

    return decoded_token


def get_user(username: str) -> Dict[str, Any]:
    idp_name = get_idp_name()
    ddb_user_name = get_ddb_user_name(username, idp_name)
    dynamodb = boto3.resource("dynamodb")
    users_table_name = os.environ["DDB_USERS_TABLE_NAME"]
    response = (
        dynamodb.Table(users_table_name)
        .get_item(Key={"username": ddb_user_name})
        .get("Item")
    )
    if not response:
        raise Exception(f"User {username} does not exist")
    if not isinstance(response, dict):
        raise Exception("Unexpected type of DDB response")

    return response if isinstance(response, dict) else {}


def get_all_admin_groups() -> List[str]:
    dynamodb = boto3.resource("dynamodb")
    groups_table_name = os.environ["DDB_GROUPS_TABLE_NAME"]
    groups_table = dynamodb.Table(groups_table_name)
    admin_groups = []
    last_evaluated_key = None
    while True:
        response = (
            (groups_table.scan())
            if not last_evaluated_key
            else groups_table.scan(LastEvaluatedKey=last_evaluated_key)
        )
        items = response.get("Items", [])
        for item in items:
            if item.get("role", "") == ADMIN_ROLE:
                admin_groups.append(str(item.get("group_name", "")))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            break

    return admin_groups


def is_any_group_admin(
    user_groups: List[str],
) -> bool:
    all_admin_groups = get_all_admin_groups()
    return any(user_group in all_admin_groups for user_group in user_groups)


def get_idp_name() -> typing.Optional[str]:
    cluster_settings_table_name = os.environ["DDB_CLUSTER_SETTINGS_TABLE_NAME"]
    dynamodb = boto3.resource("dynamodb")
    response = (
        dynamodb.Table(cluster_settings_table_name)
        .get_item(Key={"key": "identity-provider.cognito.sso_idp_provider_name"})
        .get("Item")
    )
    if not response:
        return None
    return str(response["value"])


def get_ddb_user_name(username: str, idp_name: typing.Union[str, None]) -> str:
    """
    For a user with
    1. email = a@example.org
    2. SSO enabled with identity-provider-name = idp
    Cognito creates a user as idp_a@example.org and that name is passed as username in access token.
    This method gets the identity-provider-name prefix from database and removes that from the username
    to get the user name back.
    """
    if not idp_name:
        # IdP is not set up, treat the user as Cognito native user
        return username.split("@")[0]

    identity_provider_prefix = (idp_name + "_").lower()
    email = username
    if username.startswith(identity_provider_prefix):
        email = username.replace(identity_provider_prefix, "", 1)
    return email.split("@")[0]


def verify_user_authorization(decoded_token: Dict[str, Any]) -> None:
    # Access the username claim from the decoded payload
    username = decoded_token.get("username")
    user = get_user(str(username))

    if not user.get("enabled", False) or not user.get("is_active", False):
        raise Exception(f"User {username} is inactive or disabled")
    if not user.get("role") == ADMIN_ROLE and not is_any_group_admin(
        user.get("additional_groups", [])
    ):
        raise Exception(f"User {username} is not authorized")


class AWSRequestInfo:
    def __init__(
        self,
        http_method: str,
        host: str,
        region: str,
        service_name: str,
        path: str,
        queries: Dict[str, str],
        body: str,
        headers: Dict[str, str],
        role_arn: str,
    ):
        self.http_method = http_method
        self.host = host
        self.region = region
        self.service_name = service_name
        self.path = path
        self.queries = queries
        self.body = body
        self.headers = headers
        self.role_arn = role_arn


class InvalidRequestException(Exception):
    pass


def get_assumed_role_creds(role_arn: str, user_name: str) -> Any:
    base_session = boto3.session.Session()
    fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
        client_creator=typing.cast(
            typing.Callable[[], BaseClient], base_session.client
        ),
        source_credentials=base_session.get_credentials(),
        role_arn=role_arn,
        extra_args={"RoleSessionName": user_name},
    )
    creds = botocore.credentials.DeferredRefreshableCredentials(
        method="assume-role",
        refresh_using=fetcher.fetch_credentials,
        time_fetcher=lambda: datetime.now(tzlocal()),
    )
    return creds


def parse_event_path(
    request_path: str, default_region: str
) -> typing.Tuple[str, str, str, str]:
    # /awsproxy/${REGION}/${SERVICE}/${PATH}
    pattern = r"^\/awsproxy\/([a-z]{2}-[a-z-]+-[1|2]{1}\/)?(_\/)?([a-z0-9-]+)(\/[a-z0-9-\/]+)?[\/]?$"
    match = re.match(pattern, request_path)

    if match:
        service_name = match.group(3)
        # Requester pass in _ to use default region
        use_default_region = match.group(2)
        use_specific_region = match.group(1)
        region = default_region
        if service_name == "budgets":
            # Budgets service only work with credentials signed with us-east-1
            # When you use a general endpoint, AWS routes the API request to US East (N. Virginia) (us-east-1), which is the default Region for API calls.
            # From AWS documentation https://docs.aws.amazon.com/general/latest/gr/rande.html#global-endpoints
            region = "us-east-1"
        # Do not put region in host when it is not passed in
        # Global services does not have regional endpoint
        host = f"{service_name}.amazonaws.com"
        # Can not pass in both specific region and "_" for default region
        if use_default_region and use_specific_region:
            raise InvalidRequestException(f"Invalid event path: {request_path}")
        elif use_specific_region:
            region = use_specific_region.replace("/", "")
            host = f"{service_name}.{region}.amazonaws.com"
        elif use_default_region:
            region = default_region
            host = f"{service_name}.{region}.amazonaws.com"
        path = match.group(4) or "/"
        return service_name, region, path, host
    else:
        raise InvalidRequestException(f"Invalid event path: {request_path}")


def sigv4_auth(aws_request_info: AWSRequestInfo, user_name: str) -> None:
    "Adds authorization headers for sigv4 to headers parameter."
    request_parameters = urllib.parse.urlencode(aws_request_info.queries)
    url = f"https://{aws_request_info.host}{aws_request_info.path}?{request_parameters}"
    creds = get_assumed_role_creds(aws_request_info.role_arn, user_name)

    request = botocore.awsrequest.AWSRequest(
        method=aws_request_info.http_method,
        url=url,
        data=aws_request_info.body or None,
    )
    botocore.auth.SigV4Auth(
        creds, aws_request_info.service_name, aws_request_info.region
    ).add_auth(request)
    prepared_request = request.prepare()

    aws_request_info.headers["host"] = aws_request_info.host
    for k, value in prepared_request.headers.items():
        aws_request_info.headers[k] = value
    aws_request_info.headers.pop("content-length", None)
    aws_request_info.headers["content-type"] = "application/x-amz-json-1.1"
    # Uncomment for local development
    # aws_request_info.headers["access-control-allow-origin"] = "http://localhost:3000"


def get_aws_request_info_from_event(
    event: Dict[str, Any], default_region: str
) -> AWSRequestInfo:
    # map: /awsproxy/${REGION}/${SERVICE}/${PATH}?${PARAMS}
    # to: https://${SERVICE}.${REGION}.amazonaws.com/${PATH}?${PARAMS}
    try:
        service_name, region, path, host = parse_event_path(
            event["path"], default_region
        )
        headers = event["headers"]
        headers.pop("authorization", None)
        aws_request_info = AWSRequestInfo(
            event["httpMethod"],
            host,
            region,
            service_name,
            path,
            event["queryStringParameters"],
            event["body"],
            headers,
            str(os.environ["ASSUME_ROLE_ARN"]),
        )
    except KeyError as key_error:
        raise InvalidRequestException(
            f"Invalid event: attribute {key_error} is required in event"
        )
    return aws_request_info


def send_aws_request(
    aws_request_info: AWSRequestInfo,
    user_name: str,
    attach_credentials_to_event: bool = True,
) -> HTTPResponse:
    if attach_credentials_to_event:
        sigv4_auth(aws_request_info, user_name)
    conn = http.client.HTTPSConnection(aws_request_info.host)

    conn.request(
        aws_request_info.http_method,
        aws_request_info.path,
        body=aws_request_info.body,
        headers=aws_request_info.headers,
    )
    response = conn.getresponse()

    return response


def get_sanitized_response(response: HTTPResponse) -> Any:
    content = response.read()
    status = response.status
    reason = response.reason
    # For 401 and 403 error, return generic error message.
    # For other errors, return error message from response.
    if status in [401, 403] or reason in [
        "Unauthorized",
        "Forbidden",
    ]:
        response_body = json.dumps({"error": reason})
        # Print Service response for debug purposes
        print(content.decode("utf-8"))
    else:
        response_body = content.decode("utf-8")
    return get_response(status, reason, response_body, dict(response.getheaders()))


def write_audit_log(
    event: Dict[str, Any],
    context: Any,
    decoded_token: typing.Optional[Dict[str, Any]] = None,
) -> None:
    # We have a mix of camel and snake case here
    # to keep the original attributes name as they appear in event and context
    audit_log_entry = {
        "aws_request_id": context.aws_request_id,
        "httpMethod": event.get("httpMethod", ""),
        "path": event.get("path", ""),
        "queryStringParameters": event.get("queryStringParameters", {}),
        "user-agent": event.get("headers", {}).get("user-agent", ""),
        "x-amzn-trace-id": event.get("headers", {}).get("x-amzn-trace-id", ""),
        "x-forwarded-for": event.get("headers", {}).get("x-forwarded-for", ""),
        "username": decoded_token.get("username", "") if decoded_token else None,
        "sub": decoded_token.get("sub", "") if decoded_token else None,
    }
    print("Received incoming request", json.dumps(audit_log_entry))


def handle_proxy_event(event: Dict[str, Any], context: Any) -> Any:
    attach_credentials_to_event = False
    if event.get("httpMethod", "") != "OPTIONS":
        attach_credentials_to_event = True
        # Extract the JWT token from the Authorization header
        auth_header = event.get("headers", {}).get("authorization", "")
        jwt_token = (
            auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
        )
        decoded_token = {}
        if not jwt_token:
            write_audit_log(event, context)
            return unauthorized_response(message="JWT token is missing")

        try:
            decoded_token = decode_jwt(jwt_token)
        except Exception as e:
            print(e)
            return unauthorized_response()
        finally:
            write_audit_log(event, context, decoded_token)

        try:
            verify_user_authorization(decoded_token)
        except Exception as e:
            print(e)
            return forbidden_response()
    else:
        write_audit_log(event, context)
        decoded_token = {"username": "RESProxy"}

    default_region = context.invoked_function_arn.split(":")[3]
    try:
        aws_request_info = get_aws_request_info_from_event(event, default_region)
        print(f"Forwarding request to AWS Service {aws_request_info.service_name}")
        response = send_aws_request(
            aws_request_info, decoded_token["username"], attach_credentials_to_event
        )
        print(
            "Received service response", response.status, response.reason, response.msg
        )
        return get_sanitized_response(response)
    except InvalidRequestException as exception:
        return get_bad_request_response(exception)


def unauthorized_response(message: str = "Unauthorized") -> Dict[str, Any]:
    return get_response(
        401,
        "Unauthorized",
        json.dumps({"message": message}),
    )


def forbidden_response(message: str = "Forbidden") -> Dict[str, Any]:
    return get_response(
        403,
        "Forbidden",
        json.dumps({"message": message}),
    )


def get_bad_request_response(exception: Exception) -> Any:
    response_body = json.dumps({"error": str(exception)})
    return get_response(400, "Bad Request", response_body)


def get_response(
    status_code: int,
    reason: str,
    body: str,
    headers: typing.Optional[Dict[str, Any]] = None,
    is_base64_encoded: bool = False,
) -> Dict[str, Any]:
    if headers is None:
        headers = {"Content-Type": "application/json"}
    headers["Content-Type"] = "application/json"
    return {
        "isBase64Encoded": is_base64_encoded,
        "statusCode": status_code,
        "statusDescription": f"{status_code} {reason}",
        "headers": headers,
        "body": body,
    }
