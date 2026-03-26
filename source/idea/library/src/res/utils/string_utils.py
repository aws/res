#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import re


def validate_input(input_string: str, validation_regex: str) -> bool:
    return bool(re.match(validation_regex, input_string))
