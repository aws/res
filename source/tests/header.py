#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import itertools
import pathlib

header_lines = [
    "#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.",
    "#  SPDX-License-Identifier: Apache-2.0",
]

shebangs = {
    "#!/usr/bin/env bash",
}


def test_headers_exist() -> None:
    # TODO: Change the path to include all the source files
    paths = itertools.chain(
        pathlib.Path("source/idea").glob("**/*.py"),
        pathlib.Path("source/idea").glob("**/*.sh"),
    )
    for path in paths:
        if path.parts[2].startswith("idea-"):
            continue
        if path.stat().st_size > 0:
            with open(path) as f:
                for line in header_lines:
                    current_line = f.readline().strip()
                    if current_line in shebangs:
                        current_line = f.readline().strip()
                    assert (
                        line == current_line
                    ), f"{path} does not contain a valid copyright header"
