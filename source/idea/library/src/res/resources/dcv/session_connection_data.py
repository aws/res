#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

from res.resources.dcv import session_token

# The DCV connection gateway proxies client connections to
# https://{dcv_server}:{port}{web_url_path}, so this value must match the
# path the DCV server is listening on. RES does not customize the DCV
# server's web URL path, so it defaults to "/".
DEFAULT_WEB_URL_PATH = "/"


def get_session_connection_data(session_id: str, username: str) -> Dict[str, Any]:
    """Build connection data for a DCV session.

    Assumes session_id and username have been validated at the API layer.

    :param session_id: DCV session ID
    :param username: the authenticated and authorized user
    :return: dict with connection token and web URL path
    """
    connection_token = session_token.generate_connection_token(username, session_id)

    return {
        "connectionToken": connection_token,
        "webUrlPath": DEFAULT_WEB_URL_PATH,
    }
