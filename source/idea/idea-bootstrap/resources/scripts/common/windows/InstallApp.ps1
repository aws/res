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

function Install-Virtual-Desktop-App
{
  Param(
    [Parameter(Mandatory = $true)]
    [string]$ENVName,

    [Parameter(Mandatory = $true)]
    [string]$ModuleID,

    [Parameter(Mandatory = $true)]
    [string]$ProjectName,

    [Parameter(Mandatory = $true)]
    [string]$SessionOwner,

    [Parameter(Mandatory = $true)]
    [string]$SessionId,

    [Parameter(Mandatory = $true)]
    [string]$CustomBrokerApi,

    [Parameter(Mandatory = $true)]
    [string]$OnVDIConfiguredCommands
  )

  $Region = Get-EC2InstanceMetadata -Category Region
  $AWSRegion = $Region.SystemName

  $InstallationLog = "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\AppInstallation.log.$timestamp"
  Start-Transcript -Path $InstallationLog -NoClobber -IncludeInvocationHeader

  . "C:\Users\Administrator\RES\Bootstrap\scripts\virtual-desktop-host\windows\Install.ps1"
  RequestAndExportAwsCredentials -AWSRegion $AWSRegion -CustomBrokerApi $CustomBrokerApi
  $env:AWS_DEFAULT_PROFILE = "bootstrap_profile"
  Set-AWSCredential -ProfileName "bootstrap_profile"

  # Download the Virtual Desktop Application from S3
  $BootstrapDir = "C`:\\Users\\Administrator\\RES\\Bootstrap"
  $AppPackageUriKey = @{
    "key" = "vdi-app.app_package_uri"
  } | ConvertTo-DDBItem

  Write-Host "ENVName: $ENVName, -Key: $AppPackageUriKey"

  Import-Module AWSPowerShell -Force
  $result = Get-DDBItem -TableName "$ENVName.cluster-settings" -Key $AppPackageUriKey | ConvertFrom-DDBItem
  $AppPackageURI = $result.value
  $AppPackageArchive = Split-Path $AppPackageURI -Leaf
  $PackageName = [System.IO.Path]::GetFileNameWithoutExtension($AppPackageURI)
  $urlParts = $AppPackageURI -Split "/", 4
  $bucketName = $urlParts[2]
  $key = $urlParts[3]
  Copy-S3Object -BucketName $bucketName -Key $key -LocalFile "$BootstrapDir\\$AppPackageArchive" -Force -ProfileName "bootstrap_profile"

  Write-Host  "Fetchings virtual-desktop-app from $AppPackageUriKey"

  $AppName = "virtual-desktop-app"
  $PackageDir = "${BootstrapDir}/${AppName}"
  if (!(Test-Path "$PackageDir"))
  {
    New-Item -itemType Directory -Path "$PackageDir"
  }
  Tar -xf "$BootstrapDir\\$AppPackageArchive" -C "$PackageDir"

  # Install the Virtual Desktop Application and its dependencies
  pip install -r "$PackageDir\\requirements.txt"

  pip install --no-build-isolation $( ls "$PackageDir\*-lib.tar.gz" )

  # Launch the Virtual Desktop Application and create the scheduled task to restart the application upon reboot
  $AppDeployDir = "C`:\\Program Files\\RES\\app"
  Write-Host "Extracting and copying file into: $AppDeployDir"

  if (!(Test-Path "$AppDeployDir\\$AppName"))
  {
    New-Item -itemType Directory -Path "$AppDeployDir\\$AppName"
  }
  if (!(Test-Path "$AppDeployDir\\logs"))
  {
    New-Item -itemType Directory -Path "$AppDeployDir\\logs"
  }

  $RESVDIAppLog =  "$AppDeployDir\\logs\\stdout.log"
  $VDIAppRestartNotificationContent = @"
. 'C:\Users\Administrator\RES\Bootstrap\scripts\virtual-desktop-host\windows\Install.ps1'
RequestAndExportAwsCredentials -AWSRegion "$AWSRegion" -CustomBrokerApi "$CustomBrokerApi"
Set-AWSCredential -ProfileName "bootstrap_profile"
`$env:environment_name = "$ENVName"
`$env:AWS_DEFAULT_PROFILE = "bootstrap_profile"
`$env:AWS_DEFAULT_REGION = "$AWSRegion"
`$env:AWS_REGION = "$AWSRegion"
`$env:RES_BASE_OS = "windows"
`$env:PROJECT_NAME = "$ProjectName"
`$env:IDEA_SESSION_ID = "$SessionId"
`$env:IDEA_SESSION_OWNER = "$SessionOwner"
`$env:SESSION_OWNER = "$SessionOwner"
`$env:IDEA_APP_DEPLOY_DIR = "$AppDeployDir"
`$env:IDEA_MODULE_ID = "$ModuleID"
`$env`:ON_VDI_CONFIGURED_COMMANDS = `"$OnVDIConfiguredCommands`"
resserver > "$RESVDIAppLog" 2>&1
"@

  $IdeaScriptsDirectory = "C:\IDEA\LocalScripts"
  mkdir $IdeaScriptsDirectory -Force
  Set-Content -Path "$IdeaScriptsDirectory\VDIAppRestartNotification.ps1" -Value "$VDIAppRestartNotificationContent" -Force
  schtasks /create /sc onstart /tn VDIAppRestartNotification /tr "powershell -ExecutionPolicy Bypass -File $IdeaScriptsDirectory\VDIAppRestartNotification.ps1" /ru system /f
  Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File $IdeaScriptsDirectory\VDIAppRestartNotification.ps1" -WindowStyle Hidden

  Stop-Transcript
}

