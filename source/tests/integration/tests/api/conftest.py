#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Auto-mark everything under tests/api/ as the ``dev`` suite.

These are fast API-contract / validation / dry-run checks (no VDI provisioning),
which is exactly what the ``dev`` suite selects. Applying the marker here keeps the
individual test files free of suite-marker boilerplate while still letting
``invoke integ-tests.dev`` (-m "dev") collect them. The existing
``invoke integ-tests.api`` task selects by path and is unaffected by markers.
"""

import pathlib

import pytest

_API_DIR = pathlib.Path(__file__).parent


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    # This hook receives ALL session items (not just those under this directory),
    # so restrict the marker to tests physically located under tests/api/.
    for item in items:
        item_path = pathlib.Path(str(item.fspath))
        if _API_DIR in item_path.parents:
            item.add_marker(pytest.mark.dev)
