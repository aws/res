#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pathlib


def get_commands_for_scripts(paths: list[str]) -> list[str]:
    commands = []
    root = pathlib.Path("source").parent
    scripts = root / "source/idea/pipeline/scripts"
    for raw_path in paths:
        path = pathlib.Path(raw_path)
        if not path.exists():
            raise ValueError(f"script path doesn't exist: {path}")
        if not path.is_relative_to(scripts):
            raise ValueError(f"script path isn't in {scripts}: {path}")
        relative = path.relative_to(root)
        commands.append(f"chmod +x {relative}")
        commands.append(str(relative))
    return commands
