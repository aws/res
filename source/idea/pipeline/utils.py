#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pathlib


def get_commands_for_scripts(paths: list[str]) -> list[str]:
    commands = []
    root = pathlib.Path("source").parent
    for raw_path in paths:
        path = pathlib.Path(raw_path)
        if not path.exists():
            raise ValueError(f"script path doesn't exist: {path}")
        relative = path.relative_to(root)
        commands.append(f"chmod +x {relative}")
        commands.append(str(relative))
    return commands
