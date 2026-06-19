#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from res.utils import jinja2_utils  # type: ignore


class BootstrapUserDataBuilder:
    """
    generic user data script builder for all ec2 instances launched by IDEA bootstrap framework
    todo: refactor windows script implementation to use jinja2 based templates via SDK resources
    """

    def __init__(
        self,
        base_os: str,
        aws_region: str,
        bootstrap_package_uri: str,
        install_commands: List[str],
        infra_config: Optional[Dict[str, str]] = None,
        proxy_config: Optional[Dict[str, str]] = None,
    ):
        self.base_os = base_os
        self.aws_region = aws_region
        self.bootstrap_package_uri = bootstrap_package_uri
        self.install_commands = install_commands
        self.infra_config = infra_config
        self.proxy_config = proxy_config

        script_dir = Path(os.path.abspath(__file__))
        bootstrap_source_dir_path = str(script_dir.parent)

        self.jinja_env = jinja2_utils.env_using_file_system_loader(
            bootstrap_source_dir_path
        )

    def build(self) -> Any:
        if self.base_os.lower() == "windows":
            if self.infra_config:
                raise Exception("infra config is not supported for windows")
            return self._build_windows_userdata()

        return self._render_template(
            "/_templates/linux/bootstrap_userdata_linux.sh.jinja2"
        )

    def _build_windows_userdata(self) -> str:
        userdata = rf"""
<powershell>
 $BootstrapDir = "C`:\\Users\\Administrator\\RES\\Bootstrap"
 function Install-AWSCLI {{
    $AWSCLIInstalled = $false
    try {{
        $AWSCLIVersion = aws --version 2>$null
        if ($AWSCLIVersion -and $AWSCLIVersion -match "aws-cli/2") {{
        $AWSCLIInstalled = $true
        }}
    }} catch {{
        $AWSCLIInstalled = $false
    }}

    if (!$AWSCLIInstalled) {{
        Write-Host "Installing AWS CLI v2..."
        Start-Job -Name AWSCLIWebReq -ScriptBlock {{ Invoke-WebRequest -uri https://awscli.amazonaws.com/AWSCLIV2.msi -OutFile C:\Windows\Temp\AWSCLIV2.msi }}
        Wait-Job -Name AWSCLIWebReq
        Invoke-Command -ScriptBlock {{Start-Process "msiexec.exe" -ArgumentList "/I C:\Windows\Temp\AWSCLIV2.msi /quiet /norestart" -Wait}}
        $env:Path += ";C:\Program Files\Amazon\AWSCLIV2"
        Write-Host "AWS CLI v2 installed."
    }} else {{
        Write-Host "AWS CLI v2 is already installed."
    }}
 }}
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
 $AWSPowerShellVersion = "4.1.648"
 $AWSPowerShellModule = Get-Module AWSPowerShell -ListAvailable
 if (-not $AWSPowerShellModule -or (($AWSPowerShellModule | Sort-Object Version -Descending)[0].Version -lt [Version]$AWSPowerShellVersion)) {{
     Install-PackageProvider NuGet -Force
     Install-Module -Name AWSPowerShell -Force
 }}
 Install-AWSCLI
 Download-RES-Package {self.bootstrap_package_uri}
"""
        for install_command in self.install_commands:
            userdata += f"{install_command}{os.linesep}"
        userdata += "</powershell>"
        return userdata

    def _render_template(self, template_name: str) -> Any:
        template = self.jinja_env.get_template(template_name)
        return template.render(
            base_os=self.base_os,
            aws_region=self.aws_region,
            bootstrap_package_uri=self.bootstrap_package_uri,
            install_commands=self.install_commands,
            infra_config=self.infra_config,
            proxy_config=self.proxy_config,
        )
