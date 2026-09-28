#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import base64
import re
import typing

import validators
from password_generator import PasswordGenerator
from res.constants import COGNITO_USERNAME_REGEX, USERS_TABLE_NAME
from res.resources import cluster_settings
from res.utils import table_utils

DEFAULT_LOGIN_SHELL = "/bin/bash"
USER_HOME_DIR_BASE = "/home"
EXCLUDED_USERNAMES = [
    "root",
    "admin",
    "administrator",
    "ec2-user",
    "centos",
    "ssm-user",
]
DEFAULT_ENCODING = "utf-8"
COGNITO_DOMAIN_URL_KEY = "identity-provider.cognito.domain_url"
COGNITO_MIN_ID_INCLUSIVE = 2000200001


def cognito_user_pool_domain_url() -> str:
    return cluster_settings.get_setting(COGNITO_DOMAIN_URL_KEY)


def encode_basic_auth(username: str, password: str) -> str:
    value = f"{username}:{password}"
    value = value.encode(DEFAULT_ENCODING)
    value = base64.b64encode(value)
    return str(value, DEFAULT_ENCODING)


def sanitize_username(username: str) -> str:
    if not username:
        raise Exception("username is required")
    return username.strip().lower()


def sanitize_email(email: str) -> str:
    if not email:
        raise Exception("email is required")

    email = email.strip().lower()

    if not validators.email(email):
        raise Exception(f"invalid email: {email}")

    return email


def sanitize_sub(sub: str) -> str:
    if not sub:
        raise Exception("sub is required")

    sub = sub.strip().lower()

    if not validators.uuid(sub):
        raise Exception(f"invalid sub(expected UUID): {sub}")

    return sub


def check_allowed_username(username: str) -> None:
    if username.strip().lower() in EXCLUDED_USERNAMES:
        raise Exception(
            f"invalid username: {username}. Change username to prevent conflicts with local or directory system users.",
        )


def is_user_active(user: dict) -> bool:
    return user.get("is_active", False)


def validate_native_cognito_username(username: str) -> str:
    """
    Validate that a native Cognito username is well-formed.

    Native Cognito usernames must match the RES username regex and never
    contain '@'. Usernames with '@' in the non-IdP flow could be used for
    impersonation via truncation (e.g. "clusteradmin@!" resolving to
    "clusteradmin").

    This is the single source of truth for native Cognito username validation.
    It is called by auth_utils.get_ddb_user_name(),
    proxy_handler.get_ddb_user_name(), and the Cognito Pre-Signup trigger.

    Args:
        username: The raw username from the Cognito token or signup request.

    Returns:
        The validated username (unchanged).

    Raises:
        Exception: If the username does not match the allowed pattern.
    """
    if not re.match(COGNITO_USERNAME_REGEX, username):
        raise Exception(
            f"Invalid Cognito username: '{username}'. "
            f"Username must start with a lowercase letter and contain only "
            f"lowercase letters, numbers, hyphens, and underscores (max 32 chars)."
        )
    return username


def extract_idp_email(
    username: str, idp_name: typing.Union[str, None]
) -> typing.Optional[str]:
    """
    Extract the email from an IdP-prefixed Cognito username.

    Returns the email portion if the username carries the IdP prefix,
    or None if it should be treated as a native Cognito user.

    Raises if the prefix matches but the remainder is not in email format
    (prevents a native user like 'saml_clusteradmin' from resolving to
    'clusteradmin' via prefix stripping).
    """
    if not idp_name:
        return None

    identity_provider_prefix = (idp_name + "_").lower()
    if not username.startswith(identity_provider_prefix):
        return None

    email = username.replace(identity_provider_prefix, "", 1)
    if "@" not in email:
        raise Exception(
            f"Invalid IdP username: '{username}'. "
            f"Expected email format after '{idp_name}_' prefix."
        )
    return email


def get_ddb_user_name(username: str, idp_name: typing.Union[str, None]) -> str:
    """
    For a user with
    1. email = a@example.org
    2. SSO enabled with identity-provider-name = idp
    Cognito creates a user as idp_a@example.org and that name is passed as username in access token.
    This method gets the identity-provider-name prefix from database and removes that from the username
    to get the user name back.
    """
    email = extract_idp_email(username, idp_name)
    if email is None:
        return validate_native_cognito_username(username)

    users = table_utils.query(
        table_name=USERS_TABLE_NAME,
        attributes={"email": email},
        index_name="email-index",
    )
    if len(users) > 1:
        raise Exception(f"Multiple users found with email {email}")

    if not users:
        raise Exception(
            "No user found for the provided token. " "Cannot resolve username."
        )
    username = users[0]["username"]
    return username


def generate_password(
    length=8,
    min_uppercase_chars=1,
    min_lowercase_chars=1,
    min_numbers=1,
    min_special_chars=1,
) -> str:
    generator = PasswordGenerator()
    generator.maxlen = length
    generator.minlen = length
    generator.minuchars = min_uppercase_chars
    generator.minlchars = min_lowercase_chars
    generator.minnumbers = min_numbers
    generator.minschars = min_special_chars
    generator.excludeschars = "$"
    return generator.generate()
