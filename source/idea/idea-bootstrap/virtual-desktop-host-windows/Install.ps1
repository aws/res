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

function Install-NiceDCV {
  Param(
    [string]$OSVersion,
    [string]$InstanceType,
    [switch]$Update
  )

  $DCVInstalled = $false
  $DCVServiceStatus = Get-Service dcvserver -ErrorAction SilentlyContinue -Verbose

  if($DCVServiceStatus.Status){
    if($DCVServiceStatus.Status -eq 'Running'){
      Stop-Service dcvserver
    }
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
    if($DCVSMServiceStatus.Status -eq 'Running'){
      Stop-Service DcvSessionManagerAgentService
    }
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

function Install-WindowsEC2Instance {
  Param(
    [switch]$ConfigureForRESVDI,
    [switch]$Update
  )

  $timestamp = Get-Date -Format 'yyyyMMddTHHmmssffffZ'
  $RESInstallVDI = "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\RESInstallVDI.log.$timestamp"

  Start-Transcript -Path $RESInstallVDI -NoClobber -IncludeInvocationHeader

  [string]$IMDS_Token = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token-ttl-seconds" = "600"} -Method PUT -Uri http://169.254.169.254/latest/api/token -Verbose
  $OSVersion = ((Get-ItemProperty -Path "Microsoft.PowerShell.Core\Registry::\HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion" -Name ProductName -Verbose).ProductName) -replace  "[^0-9]" , ''
  $InstanceType = Invoke-RestMethod -Headers @{'X-aws-ec2-metadata-token' = $IMDS_Token} -Method GET -Uri http://169.254.169.254/latest/meta-data/instance-type -Verbose

  Install-NiceDCV -OSVersion $OSVersion -InstanceType $InstanceType -Update:$Update
  Install-NiceSessionManagerAgent -Update:$Update

  Stop-Transcript

  if($ConfigureForRESVDI){
    Import-Module .\Configure.ps1
    Configure-WindowsEC2Instance
  }
}
