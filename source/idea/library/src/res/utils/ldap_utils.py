#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any


def ldap_str(val: Any) -> Any:
    return val[0].decode("utf-8") if val else None


def ldap_int(val: Any) -> Any:
    return int(ldap_str(val)) if val else None
