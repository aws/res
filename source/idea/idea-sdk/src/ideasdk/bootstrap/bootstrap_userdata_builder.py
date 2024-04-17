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

from ideadatamodel import exceptions
from ideasdk.utils import Utils, Jinja2Utils

import os
from typing import List, Dict, Optional


class BootstrapUserDataBuilder:
    """
    generic user data script builder for all ec2 instances launched by IDEA bootstrap framework
    todo: refactor windows script implementation to use jinja2 based templates via SDK resources
    """

    def __init__(self, base_os: str, aws_region: str, bootstrap_package_uri: str, install_commands: List[str],
                 bootstrap_source_dir_path: str, infra_config: Optional[Dict] = None,
                 proxy_config: Optional[Dict] = None, substitution_support: bool = True):
        self.base_os = base_os
        self.aws_region = aws_region
        self.bootstrap_package_uri = bootstrap_package_uri
        self.install_commands = install_commands
        self.infra_config = infra_config
        self.proxy_config = proxy_config
        self.substitution_support = substitution_support

        self.jinja_env = Jinja2Utils.env_using_file_system_loader(bootstrap_source_dir_path)

    def build(self):
        if self.base_os.lower() == 'windows':
            if Utils.is_not_empty(self.infra_config):
                raise exceptions.general_exception('infra config is not supported for windows')
            return self._build_windows_userdata()

        if self.substitution_support:
            return self._render_template('/_templates/linux/bootstrap_userdata_linux_base_substitution.sh.jinja2')
        return self._render_template('/_templates/linux/bootstrap_userdata_linux_base_non_substitution.sh.jinja2')

    def _build_windows_userdata(self) -> str:
        userdata = f'''
<powershell>
 $BootstrapDir = "C`:\\Users\\Administrator\\RES\\Bootstrap"
 function Download-RES-Package {{
     Param(
     [ValidateNotNullOrEmpty()]
     [Parameter(Mandatory=$true)]
     [String] $PackageDownloadURI
     )
     if (!(Test-Path "$BootstrapDir")) {{
         New-Item -itemType Directory -Path "$BootstrapDir"
     }}
     cd "$BootstrapDir"
     Write-Output $PackageDownloadURI
     $PackageArchive=Split-Path $PackageDownloadURI -Leaf
     $PackageName = [System.IO.Path]::GetFileNameWithoutExtension($PackageDownloadURI)
     if ($PackageDownloadURI -like "s3`://*") {{
        $urlParts = $PackageDownloadURI -Split "/", 4
        $bucketName = $urlParts[2]
        $key = $urlParts[3]
        Copy-S3Object -BucketName $bucketName -Key $key -LocalFile "$BootstrapDir\\$PackageArchive" -Force
     }} else {{
        Copy-Item -Path $PackageDownloadURI -Destination "$BootstrapDir\\$PackageArchive"
     }}
     Tar -xf "$BootstrapDir\\$PackageArchive"
 }}
 Download-RES-Package {self.bootstrap_package_uri}
'''
        for install_command in self.install_commands:
            userdata += f'{install_command}{os.linesep}'
        userdata += '</powershell>'
        return userdata

    def _render_template(self, template_name):
        template = self.jinja_env.get_template(template_name)
        return template.render(
            base_os=self.base_os,
            aws_region=self.aws_region,
            bootstrap_package_uri=self.bootstrap_package_uri,
            install_commands=self.install_commands,
            infra_config=self.infra_config,
            proxy_config=self.proxy_config
        )
