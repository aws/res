#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

from connexion.exceptions import OAuthProblem
from res.resources import token as token_resource  # type: ignore


def bearer_auth(token, request):
    """
    Validate client credentials access token from Cognito.

    Verifies the token signature, expiration, and scope.
    """
    try:
        decoded = token_resource.decode_token(token=token, verify_exp=True)

        expected_scope = f"{os.environ['environment_name']}-dcv-session-manager/sm_scope"
        if expected_scope not in decoded.get("scope", "").split():
            raise OAuthProblem("Insufficient scope")

        return {"authenticated": True}
    except OAuthProblem:
        raise
    except Exception as e:
        raise OAuthProblem(detail=f"Token validation failed: {e}")
