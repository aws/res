#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import os
import sys


class SubdirFinder(importlib.abc.MetaPathFinder):
    """
    Custom finder that allows importing modules from subdirectories as if they
    were directly under the parent package.

    e.g. with prefix='datamodel.models.' and subdirs=['backend', 'dcv_session_management'],
    'from datamodel.models.xxx import X' resolves to datamodel/models/backend/xxx.py
    """

    def __init__(self, parent_dir: str, prefix: str, subdirs: list[str]):
        self._parent_dir = parent_dir
        self._prefix = prefix
        self._subdirs = subdirs

    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith(self._prefix):
            return None

        relative = fullname[len(self._prefix):]
        if "." in relative:
            return None

        matches = [
            (subdir, os.path.join(self._parent_dir, subdir, f"{relative}.py"))
            for subdir in self._subdirs
            if os.path.isfile(os.path.join(self._parent_dir, subdir, f"{relative}.py"))
        ]
        if len(matches) > 1:
            dirs = [m[0] for m in matches]
            raise ImportError(
                f"Ambiguous import '{fullname}': found in subdirs {dirs}"
            )
        if not matches:
            return None

        subdir, candidate = matches[0]
        spec = importlib.util.spec_from_file_location(
            fullname, candidate
        )
        _original_exec = spec.loader.exec_module

        def _exec_and_alias(module, _orig=_original_exec, _canon=f"{self._prefix}{subdir}.{relative}"):
            if _canon in sys.modules:
                sys.modules[module.__name__] = sys.modules[_canon]
                return
            _orig(module)
            sys.modules[_canon] = module

        spec.loader.exec_module = _exec_and_alias
        return spec


def install(parent_dir: str, prefix: str, subdirs: list[str]):
    """Install a SubdirFinder on sys.meta_path."""
    sys.meta_path.insert(0, SubdirFinder(parent_dir, prefix, subdirs))
