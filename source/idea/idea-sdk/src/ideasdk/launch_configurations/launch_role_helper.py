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


class LaunchRoleHelper:

    @staticmethod
    def get_vdi_role_path(cluster_name: str, region: str, path: str="") -> str:
        return f'{path}{cluster_name}-{region}/vdi'

    @staticmethod
    def get_vdi_instance_profile_path(cluster_name: str, region: str, path: str="") -> str:
        return LaunchRoleHelper.get_vdi_role_path(cluster_name, region, path)

    @staticmethod
    def get_vdi_role_name(cluster_name: str, project_name: str, prefix: str="") -> str:
        return f'{prefix}{cluster_name}-vdi-{project_name}'

    @staticmethod
    def get_vdi_instance_profile_name(cluster_name: str, project_name: str, prefix: str="") -> str:
        return LaunchRoleHelper.get_vdi_role_name(cluster_name, project_name, prefix)
