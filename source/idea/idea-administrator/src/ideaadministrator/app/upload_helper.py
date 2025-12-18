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


import ideaadministrator
from ideadatamodel import exceptions, constants
from ideasdk.utils import Utils

from ideasdk.context import SocaCliContext, SocaContextOptions

import os

MODULE_ID_NAME_MAP = {
    "installation": constants.MODULE_INSTALLATION_SCRIPT,
    "broker": "dcv-broker",
    "gateway": "dcv-connection-gateway",
    "vdi-app": "virtual-desktop"
}


class UploadHelper:

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str, module_id: str, package_uri: str):

        if Utils.is_empty(cluster_name):
            raise exceptions.invalid_params('cluster_name is required')
        if Utils.is_empty(aws_region):
            raise exceptions.invalid_params('aws_region is required')
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('module_id is required')

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.module_id = module_id
        self.user_package_uri = package_uri

        self.context = SocaCliContext(options=SocaContextOptions(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            enable_aws_client_provider=True
        ))

        if self.module_id in MODULE_ID_NAME_MAP.keys():
            self.module_name = MODULE_ID_NAME_MAP[self.module_id]
        else:
            module_info = self.context.get_cluster_module_info(module_id)
            if module_info is None:
                raise exceptions.general_exception(f'module not found: {module_id}')
            module_type = module_info['type']
            if module_type != 'app':
                raise exceptions.general_exception(f'uploading is not supported for module: {module_id}, type: {module_type}')
            self.module_name = module_info['name']

    def upload_package_to_s3(self) -> str:
        """
        if package uri is provided by the user, check if the package uri is local or s3 path.
            if package is local, upload to cluster's s3 bucket and return uri

        if package uri is not provided, find the local package uri for current release, upload to s3 and return the s3 path.
            if running in dev mode from sources, package uri is: <PROJECT_ROOT>/dist/<package>.tar.gz
            if running in docker container, package uri is: /root/.idea/downloads/<package>.tar.gz
        """
        if Utils.is_not_empty(self.user_package_uri):
            package_uri = self.user_package_uri
        else:

            if ideaadministrator.props.is_dev_mode():
                package_dist_dir = ideaadministrator.props.dev_mode_project_dist_dir
            else:
                package_dist_dir = ideaadministrator.props.soca_downloads_dir

            if self.module_name == constants.MODULE_INSTALLATION_SCRIPT:
                package_uri = os.path.join(package_dist_dir,
                                        f'{self.module_name}.tar.gz')
            else:
                package_uri = os.path.join(package_dist_dir,
                                        f'idea-{self.module_name}-{ideaadministrator.props.current_release_version}.tar.gz')

        if package_uri.startswith('s3://'):
            return package_uri

        if not Utils.is_file(package_uri):
            raise exceptions.file_not_found(f'release package not found: {package_uri}')

        staging_s3_bucket = self.context.config().get_string('cluster.staging_bucket_name', required=True)

        s3_release_path = f'releases/{ideaadministrator.props.current_release_version}/{os.path.basename(package_uri)}'
        s3_package_uri = f's3://{staging_s3_bucket}/{s3_release_path}'
        self.context.info(f'uploading package: {package_uri} to {s3_package_uri} ...')
        self.context.aws().s3().upload_file(
            Bucket=staging_s3_bucket,
            Filename=package_uri,
            Key=s3_release_path
        )

    def apply(self):
        self.upload_package_to_s3()
