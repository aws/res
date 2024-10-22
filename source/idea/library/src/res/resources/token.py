#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import requests
from res.utils import auth_utils


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
