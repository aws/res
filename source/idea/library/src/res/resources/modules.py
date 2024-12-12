#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

from res.utils import table_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

MODULES_TABLE_NAME = "modules"
MODULES_TABLE_HASH_KEY = "module_id"
MODULES_TABLE_NAME_KEY = "name"
MODULES_TABLE_TYPE_KEY = "type"
MODULES_TABLE_STACK_KEY = "stack_name"
MODULES_TABLE_STATUS_KEY = "status"
MODULES_TABLE_VERSION_KEY = "version"


def create_module(module: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create module in DDB
    """
    module_id = module.get(MODULES_TABLE_HASH_KEY)
    if not module_id:
        raise Exception("module id is required")

    module_name = module.get(MODULES_TABLE_NAME_KEY)
    if not module_name:
        raise Exception("module name is required")

    logger.info(f"creating module {module_name}")

    module_to_create = {
        MODULES_TABLE_STATUS_KEY: "to be deployed",
        **module,
    }
    module = table_utils.create_item(
        MODULES_TABLE_NAME,
        item=module_to_create,
    )
    return module
