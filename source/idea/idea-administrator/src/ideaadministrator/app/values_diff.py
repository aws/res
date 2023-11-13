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

from ideaadministrator.app_props import AdministratorProps
import os


class ValuesDiff:

    def __init__(self, cluster_name: str, aws_region: str):
        self.props = AdministratorProps()
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.values_file = 'values.yml'
        self.values_file_dir = 'values/'

    def get_cluster_name(self) -> str:
        return self.cluster_name

    def get_aws_region(self) -> str:
        return self.aws_region

    def get_cluster_region_dir(self) -> str:
        cluster_home = self.props.cluster_dir(self.get_cluster_name())
        cluster_region_dir = self.props.cluster_region_dir(cluster_home, self.get_aws_region())
        os.makedirs(cluster_region_dir, exist_ok=True)
        return cluster_region_dir

    def get_values_file_path(self) -> str:
        return os.path.join(self.get_cluster_region_dir(), self.values_file)

    def get_values_file_s3_key(self) -> str:
        return self.values_file_dir + self.values_file

