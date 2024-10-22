#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import base64

import validators
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
