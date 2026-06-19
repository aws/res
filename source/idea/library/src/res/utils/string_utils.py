#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import re
from typing import Optional

VALID_ACTOR_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._\-]+\Z")

INVALID_ACTOR_NAME_MESSAGE = (
    "Only alphanumeric characters, dots, hyphens, and underscores are allowed."
)


def validate_input(input_string: str, validation_regex: str) -> bool:
    return bool(re.match(validation_regex, input_string))


def validate_actor_name(actor_name: Optional[str]) -> None:
    if not actor_name or not VALID_ACTOR_NAME_PATTERN.match(actor_name):
        raise ValueError(INVALID_ACTOR_NAME_MESSAGE)
