#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict, Optional

import jwt
import requests
import res.exceptions as exceptions
from jwt import PyJWKClient
from res.constants import COGNITO_USER_POOL_PROVIDER_URL
from res.resources import cluster_settings
from res.utils import auth_utils

DEFAULT_JWK_CACHE_KEYS = True
DEFAULT_JWK_MAX_CACHED_KEYS = 16
DEFAULT_KEY_ALGORITHM = "RS256"


def oauth2_access_token_url() -> str:
    return f"{auth_utils.cognito_user_pool_domain_url()}/oauth2/token"


def get_access_token_using_client_credentials(
    client_id, client_secret, client_credentials_scope
) -> str:
    """
    Gets access token using client credentials
    :param client_id:
    :param client_secret:
    :param client_credentials_scope:
    :returns successful and unsuccessul list of stopped sessions
    """
    if not client_id or not client_secret or not client_credentials_scope:
        return ""
    access_token_url = oauth2_access_token_url()
    basic_auth = auth_utils.encode_basic_auth(client_id, client_secret)
    scope = client_credentials_scope

    response = requests.post(
        url=access_token_url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}",
        },
        data={"grant_type": "client_credentials", "scope": scope},
    )
    result = response.json()
    return result.get("access_token")


def decode_token(token: str, verify_exp: Optional[bool] = True) -> Dict:
    """
    decodes the JWT token and verifies signature and expiration.

    should be used by all daemon services that expose a public API to validate tokens and authorize API resources using scope or
    additional metadata from the token.

    :param token: the JWT token.
    :param verify_exp: indicates if expiration time should be verified. useful in scenarios where the token could be expired, but
    service needs to extract other information from the token.
    :return: A dict object of decoded token.
    :raises AUTH_TOKEN_EXPIRED if token is expired.
    :raises UNAUTHORIZED_ACCESS if token is invalid
    """
    try:

        if not token:
            raise exceptions.UnauthorizedAccess(error_code="MISSING_TOKEN")

        jwk_client = PyJWKClient(
            uri=f"{cluster_settings.get_setting(COGNITO_USER_POOL_PROVIDER_URL)}/.well-known/jwks.json",
            cache_keys=DEFAULT_JWK_CACHE_KEYS,
            max_cached_keys=DEFAULT_JWK_MAX_CACHED_KEYS,
        )
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=[DEFAULT_KEY_ALGORITHM],
            options={"verify_exp": verify_exp},
        )
        return decoded_token
    except jwt.ExpiredSignatureError:
        # these are normal errors, and will occur during everyday operations
        # clients should renew the access token upon receiving this error code.
        raise exceptions.AuthTokenExpired(
            error_code="AUTH_TOKEN_EXPIRED", message=f"Token Expired"
        )
    except jwt.InvalidTokenError as e:
        # this is not normal, and log entries should be monitored to check why tokens are invalid.
        raise exceptions.UnauthorizedAccess(
            error_code="INVALID_TOKEN", message=f"Invalid Token - {e}"
        )
