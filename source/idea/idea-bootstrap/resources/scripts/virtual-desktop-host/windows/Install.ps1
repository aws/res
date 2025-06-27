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

function Check-Python-Installed {
  $PythonInstalled = $false
  $PythonCommand = Get-Command python -ErrorAction SilentlyContinue

  if ($PythonCommand) {
      $PythonVersion = python --version
      if ($PythonVersion -match "3\.11") {
          $PythonInstalled = $true
      }
  }
  return $PythonInstalled
}

function Install-Python {
  $PythonInstalled = Check-Python-Installed

  if(!$PythonInstalled){
    Start-Job -Name PythonWebReq -ScriptBlock { Invoke-WebRequest -uri https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe -OutFile C:\Windows\Temp\Python3.11.0.exe }
    Wait-Job -Name PythonWebReq

    Invoke-Command -ScriptBlock {Start-Process "C:\Windows\Temp\Python3.11.0.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait}

    $oldPath = [Environment]::GetEnvironmentVariable("Path")
    $newPythonPath = "C:\Program Files\Python311\Scripts\;C:\Program Files\Python311"
    $newPath = "$newPythonPath;$oldPath"

    [Environment]::SetEnvironmentVariable("Path", $newPath)
  }
}

function Install-Python-Requirements {
  Param(
    [switch]$PrebakeAMI
  )
  pip install -r $env:SystemDrive\Users\Administrator\RES\Bootstrap\scripts\vdi-helper\requirements.txt

  if($PrebakeAMI)
  {
    pip install -r $env:SystemDrive\Users\Administrator\RES\Bootstrap\requirements.txt
  }
}

function Install-NiceDCV {
  Param(
    [string]$OSVersion,
    [string]$InstanceType,
    [switch]$Update
  )

  $DCVInstalled = $false
  $DCVServiceStatus = Get-Service dcvserver -ErrorAction SilentlyContinue -Verbose

  if($DCVServiceStatus.Status){
    $DCVInstalled = $true
  }

  if(!$DCVInstalled -or $Update){
    # Information on NICE Virtual Display Driver: https://docs.aws.amazon.com/dcv/latest/adminguide/setting-up-installing-winprereq.html#setting-up-installing-general
    if((($OSVersion -ne "2019") -and ($OSversion -ne "2022")) -and (($InstanceType[0] -ne 'g') -or ($InstanceType[0] -ne 'p'))){
        $VirtualDisplayDriverRequired = $true
    }
    if($VirtualDisplayDriverRequired){
        # Standard distribution links for NICE DCV Server and Virtual Display Driver
        Start-Job -Name DCVWebReq -ScriptBlock { Invoke-WebRequest -uri https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-virtual-display-x64-Release.msi -OutFile C:\Windows\Temp\DCVDisplayDriver.msi ; Invoke-WebRequest -uri https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi -OutFile C:\Windows\Temp\DCVServer.msi }
    }else{
        Start-Job -Name DCVWebReq -ScriptBlock { Invoke-WebRequest -uri https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi -OutFile C:\Windows\Temp\DCVServer.msi }
    }
    Wait-Job -Name DCVWebReq
    if($VirtualDisplayDriverRequired){
        Invoke-Command -ScriptBlock {Start-Process "msiexec.exe" -ArgumentList "/I C:\Windows\Temp\DCVDisplayDriver.msi /quiet /norestart" -Wait}
    }
    Invoke-Command -ScriptBlock {Start-Process "msiexec.exe" -ArgumentList "/I C:\Windows\Temp\DCVServer.msi ADDLOCAL=ALL /quiet /norestart /l*v dcv_install_msi.log " -Wait}
    while (-not(Get-Service dcvserver -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 250 }
  }

  Get-Service dcvserver -ErrorAction SilentlyContinue
}

function Install-NiceSessionManagerAgent {
  Param(
    [switch]$Update
  )

  $DCVSMInstalled = $false
  $DCVSMServiceStatus = Get-Service DcvSessionManagerAgentService -ErrorAction SilentlyContinue -Verbose

  if($DCVSMServiceStatus.Status){
    $DCVSMInstalled = $true
  }

  if(!$DCVSMInstalled -or $Update){
    # Standard distribution link for NICE DCV Session Manager Agent
    Start-Job -Name SMWebReq -ScriptBlock { Invoke-WebRequest -uri https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-session-manager-agent-x64-Release.msi -OutFile C:\Windows\Temp\DCVSMAgent.msi }
    Wait-Job -Name SMWebReq
    Invoke-Command -ScriptBlock {Start-Process "msiexec.exe" -ArgumentList "/I C:\Windows\Temp\DCVSMAgent.msi /quiet /norestart " -Wait}
    while (-not(Get-Service dcvserver -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 250 }
  }

  Get-Service DcvSessionManagerAgentService -ErrorAction SilentlyContinue
}

function Install-CloudwatchAgent {
  $CloudwatchInstalled = $false
  $CloudwatchServiceStatus = Get-Service -Name AmazonCloudWatchAgent -ErrorAction SilentlyContinue
  if($CloudwatchServiceStatus){
    Write-Host "CloudWatch agent is already installed"
    $CloudwatchInstalled = $true
  }
  if(!$CloudwatchInstalled){
    # Download
    Write-Host "Downloading CloudWatch agent installer..."
    Start-Job -Name CWWebReq -ScriptBlock { Invoke-WebRequest -uri https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/amazon-cloudwatch-agent.msi -OutFile C:\Windows\Temp\amazon-cloudwatch-agent.msi }
    Wait-Job -Name CWWebReq
    # Installation
    Write-Host "Installing CloudWatch agent..."
    Invoke-Command -ScriptBlock {Start-Process "msiexec.exe" -ArgumentList "/I C:\Windows\Temp\amazon-cloudwatch-agent.msi /quiet /norestart" -Wait}
  }
}

function Install-NVIDIAGPUDriver {
  Param(
    [string]$OSVersion,
    [switch]$Update
  )
  $ExistingDriver = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" } | Select-Object Name, DriverVersion, Status
  if ($ExistingDriver -eq $null -or $Update) {
    $Bucket = "ec2-windows-nvidia-drivers"
    $LocalPath = "C:\Windows\Temp\NVIDIA\"
    $Objects = Get-S3Object -BucketName $Bucket -Region us-east-1
    $timestamp = Get-Date -Format "MM/dd/yyyy-HH:mm:ss_K"

    if ($OSVersion -eq "2016") {
      Write-Host "NVIDIA GPU detected. Pulling GRID version < v14.2."
      $Key = ($Objects | where { $_.Key -like 'grid-14.1*' } | Sort-Object -Property LastModified -Descending)[0].Key
    }
    elseif($OSVersion -eq "2019") {
      Write-Host "NVIDIA GPU detected. Pulling GRID version < v17"
      $Key = ($Objects | where { $_.Key -like 'grid-16*' } | Sort-Object -Property LastModified -Descending)[0].Key
    }
    elseif($OSVersion -eq "2022") {
      Write-Host "NVIDIA GPU detected. Pulling latest GRID version."
      $Key = ($Objects | where { $_.Key -like 'latest*' } | Sort-Object -Property LastModified -Descending)[0].Key
    }
    else {
      Write-Host "NVIDIA drivers not found for your OS version. Skipping.."
    }
    if ($Key -ne '' -and $Object.Size -ne 0) {
      $LocalFilePath = Join-Path $LocalPath $Key
      Copy-S3Object -BucketName $Bucket -Key $Key -LocalFile $LocalFilePath -Region us-east-1
      . $LocalFilePath -s
    }
    Write-Host "NVIDIA drivers installed."
  }
  else {
    Write-Host "NVIDIA drivers already installed."
  }
}

function Install-AMDGPUDriver {
  $ExistingDriver = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*AMD*" } | Select-Object Name, DriverVersion, Status
  if ($ExistingDriver -eq $null -or $Update)
  {
    $KeyPrefix = ""
    if ($OSVersion -eq "2016")
    {
      $KeyPrefix = "archives"
    }
    elseif($OSVersion -eq "2019")
    {
      $KeyPrefix = "latest/AMD_GPU_WINDOWS_2K19" # use "archives" for Windows Server 2016
    }
    elseif($OSVersion -eq "2022")
    {
      $KeyPrefix = "latest/AMD_GPU_WINDOWS_2K22"
    }
    else
    {
      Write-Host "AMD drivers not found for your OS version. Skipping.."
    }
    $Bucket = "ec2-amd-windows-drivers"
    $LocalPath = "C:\Windows\Temp\AMD"
    $Objects = Get-S3Object -BucketName $Bucket -KeyPrefix $KeyPrefix -Region us-east-1
    foreach ($Object in $Objects)
    {
      $LocalFileName = $Object.Key
      if ($LocalFileName -ne '' -and $Object.Size -ne 0)
      {
        $LocalFilePath = Join-Path $LocalPath $LocalFileName
        Copy-S3Object -BucketName $Bucket -Key $Object.Key -LocalFile $LocalFilePath -Region us-east-1
      }
    }
    Expand-Archive $LocalFilePath -DestinationPath "$LocalPath\$KeyPrefix" -Verbose
    pnputil /add-driver $LocalPath\$KeyPrefix\*.inf /install /subdirs

    Write-Host "AMD drivers installed."
  }
  else {
    Write-Host "AMD drivers already installed."
  }
}

function Install-GPUDriver {
  Param(
    [string]$OSVersion,
    [string]$InstanceFamily,
    [switch]$Update
  )

  # refer to: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html
  # Available drivers by instance type for Grid mapping.
  switch ($InstanceFamily) {
    { "g6", "gr6", "g6e", "g5", "g4dn", "g3", "g3s" -contains $_ } {
      Install-NVIDIAGPUDriver -OSVersion $OSVersion -Update:$Update
    }
    "g4ad" {
      Install-AMDGPUDriver -OSVersion $OSVersion -Update:$Update
    }
    default {
      Write-Host "GPU drivers not found for your instance family. Skipping.."
    }
  }
}

function RequestAndExportAwsCredentials {
    param (
        [Parameter(Mandatory=$true)]
        [string]$AWSRegion,

        [Parameter(Mandatory=$true)]
        [string]$CustomBrokerApi
    )

    $BootstrapTokenPath = 'C:\VDIBootstrap\Secure\bootstrap-token'

    $AwsConfigDir = "$env:USERPROFILE\.aws"
    Remove-Item -Path "$env:USERPROFILE\.aws" -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -Path $AwsConfigDir -ItemType Directory -Force | Out-Null

    $ProfileName = "bootstrap_profile"
    $IdeaPythonPath = "python"
    $CustomBrokerPath = "C:\Users\Administrator\RES\Bootstrap\scripts\vdi-helper\custom_credential_broker.py"

    if (-not (Test-Path $CustomBrokerPath)) {
        Write-Error "Error: Custom credential broker script not found at $CustomBrokerPath"
    }

    $JwtToken = (Get-Content -Path $BootstrapTokenPath -Raw).Trim()

    # Define the output path as a variable
    $CredentialProcessPath = "C:\VDIBootstrap\Secure\CredentialProcess.ps1"

    $scriptContent = @"
# Define the Python path and script path
`$BootstrapTokenPath = 'C:\VDIBootstrap\Secure\bootstrap-token'
`$PythonPath = "$IdeaPythonPath"
`$ScriptPath = "$CustomBrokerPath"
`$CustomBrokerApi = "$CustomBrokerApi"
`$JwtToken = (Get-Content -Path `$BootstrapTokenPath -Raw).Trim()

# Build and return the command string
& `$PythonPath `$ScriptPath --bootstrap-token `$JwtToken --api-url `$CustomBrokerApi
"@

    # Create directory if it doesn't exist
    $directory = Split-Path -Path $CredentialProcessPath -Parent
    if (-not (Test-Path -Path $directory)) {
        New-Item -Path $directory -ItemType Directory -Force | Out-Null
    }

    $scriptContent | Out-File -FilePath $CredentialProcessPath -Encoding utf8 -Force

    # Configure AWS CLI settings
    aws configure set output json --profile default
    aws configure set region $AWSRegion --profile default

    # Building credentials process string
    aws configure set credential_process "powershell.exe -ExecutionPolicy Bypass -File $CredentialProcessPath" --profile 'bootstrap_profile'

    aws configure set output json --profile $ProfileName
    aws configure set region $AWSRegion --profile $ProfileName

    return $true
}

function Install-WindowsEC2Instance {
  Param(
    [string]$AWSRegion,
    [string]$ENVName,
    [string]$ModuleID,
    [string]$ProjectName,
    [string]$SessionOwner,
    [string]$SessionId,
    [string]$BootstrapToken,
    [string]$CustomBrokerApi,
    [string]$OnVDIConfiguredCommands,

    [switch]$ConfigureForRESVDI,
    [switch]$PrebakeAMI,
    [switch]$Update
  )

  $timestamp = Get-Date -Format 'yyyyMMddTHHmmssffffZ'
  $RESInstallVDI = "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\RESInstallVDI.log.$timestamp"

  Start-Transcript -Path $RESInstallVDI -NoClobber -IncludeInvocationHeader

  if (-not (Test-Path -Path "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\res_installed_all_packages.log"))
  {
    $AWSPowerShellVersion = "4.1.648"
    $AWSPowerShellModule = Get-Module AWSPowerShell -ListAvailable
    if (-not $AWSPowerShellModule -or (($AWSPowerShellModule | Sort-Object Version -Descending)[0].Version -lt [Version]$AWSPowerShellVersion))
    {
      Install-PackageProvider NuGet -Force
      Install-Module -Name AWSPowerShell -Force
    }

    [string]$IMDS_Token = Invoke-RestMethod -Headers @{ "X-aws-ec2-metadata-token-ttl-seconds" = "600" } -Method PUT -Uri http://169.254.169.254/latest/api/token -Verbose

    $OSVersion = ((Get-ItemProperty -Path "Microsoft.PowerShell.Core\Registry::\HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion" -Name ProductName -Verbose).ProductName) -replace "[^0-9]", ''
    $InstanceType = Invoke-RestMethod -Headers @{ 'X-aws-ec2-metadata-token' = $IMDS_Token } -Method GET -Uri http://169.254.169.254/latest/meta-data/instance-type -Verbose
    $InstanceFamily = $InstanceType.Split('.')[0]

    Install-NiceDCV -OSVersion $OSVersion -InstanceType $InstanceType -Update:$Update
    Install-NiceSessionManagerAgent -Update:$Update

    if ($InstanceType.Split('.')[0] -like 'g*')
    {
      Install-GPUDriver -OSVersion $OSVersion -InstanceFamily $InstanceFamily -Update:$Update
    }

    Install-Python
    if ($PrebakeAMI) {
      Install-Python-Requirements -PrebakeAMI
    }
    else {
      Install-Python-Requirements
    }
    Install-CloudwatchAgent

    Get-Date | Out-File -FilePath "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\res_installed_all_packages.log" -Append
  }

  Stop-Transcript

  if($ConfigureForRESVDI) {
    # Create a secure directory in C:VDIBootstrap\Secure
    $tokenDir = "C:\VDIBootstrap\Secure"
    New-Item -Path $tokenDir -ItemType Directory -Force

    # Set strict NTFS permissions - only Administrators and SYSTEM
    $acl = Get-Acl -Path $tokenDir
    $acl.SetAccessRuleProtection($true, $false)  # Disable inheritance, remove inherited permissions

    # Add only Administrator and SYSTEM with full control
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")

    $acl.AddAccessRule($adminRule)
    $acl.AddAccessRule($systemRule)
    Set-Acl -Path $tokenDir -AclObject $acl

    $tokenPath = Join-Path $tokenDir "bootstrap-token"

    $BootstrapToken | Out-File -FilePath $tokenPath -NoNewline -Encoding ASCII

    cd "..\..\common\windows"
    Import-Module .\InstallApp.ps1
    Install-Virtual-Desktop-App -ENVName $ENVName -ModuleID $ModuleID -ProjectName $ProjectName -SessionOwner $SessionOwner -SessionId $SessionId -CustomBrokerApi $CustomBrokerApi -OnVDIConfiguredCommands $OnVDIConfiguredCommands
  }
}
