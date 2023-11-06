#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from jinja2 import Environment, FileSystemLoader, PackageLoader, BaseLoader


class Jinja2Utils:

    @staticmethod
    def env_using_file_system_loader(search_path: str, auto_escape: bool = False) -> Environment:
        return Environment(
            loader=FileSystemLoader(
                searchpath=search_path,
                followlinks=False
            ),
            autoescape=auto_escape  # nosec B701
        )

    @staticmethod
    def env_using_package_loader(package_name: str, package_path: str, auto_escape: bool = False) -> Environment:
        return Environment(
            loader=PackageLoader(
                package_name=package_name,
                package_path=package_path
            ),
            autoescape=auto_escape  # nosec B701
        )

    @staticmethod
    def env_using_base_loader(auto_escape: bool = False) -> Environment:
        return Environment(
            loader=BaseLoader(),
            autoescape=auto_escape  # nosec B701
        )
