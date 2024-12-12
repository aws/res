#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import base64
import typing

import validators
from password_generator import PasswordGenerator
from res.resources import cluster_settings

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
