#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

BASE_OS = os.getenv("RES_BASE_OS")
if BASE_OS == "windows":
    from ideabootstrap.file_system.windows.shared_storage import configure as configure_platform
else:
    from ideabootstrap.file_system.linux.shared_storage import configure as configure_platform

def configure() -> None:
    configure_platform()
