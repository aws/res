#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

from typing import Dict

def eval_shared_storage_scope(shared_storage: Dict) -> bool:
    scope = shared_storage.get("scope", [])
    if not scope:
        return True

    def _eval_project() -> bool:
        projects = shared_storage.get("projects", [])
        if not projects:
            return False
        return project_name in projects

    def _eval_module() -> bool:
        modules = shared_storage.get("modules", [])
        # empty list = allow all
        if not modules:
            return True
        return module_name in modules

    def _eval_internal_filesystem() -> bool:
        mount_dir = shared_storage.get("mount_dir")
        if mount_dir == "/internal":
            return True
        return False

    project_name = os.environ.get("PROJECT_NAME")
    module_name = os.environ.get("IDEA_MODULE_NAME")
    # Global filesystem attached to modules vs projects
    if "cluster" in scope:
        return (
            True if not project_name else (_eval_project() or _eval_internal_filesystem())
        )

    if "module" in scope and "project" in scope:
        return _eval_module() and _eval_project()

    if "module" in scope:
        return _eval_module()

    if "project" in scope:
        return _eval_project()

    return False
