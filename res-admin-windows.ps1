######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

function Exit-Fail($message,$command) {
    Write-Host "[MESSAGE]: ${message} `n[COMMAND EXECUTED]: ${command}`n[HELP]: Refer to ${DocumentationError} for troubleshooting." -foregroundcolor "red"
    Read-Host -Prompt "Installation was not successful, press Enter to exit"
    Exit 1
}

function Verify-Command($type,$message,$command) {
    if ($type -eq "Get-Command") {
        if($Error) {
            Exit-Fail $message $command
        }
    }
    elseif ($type -eq "Invoke-Expression") {
        if($LASTEXITCODE -ne 0) {
             Exit-Fail $message $command
        }
    }
    else {
        Write-Output "type must be either Get-Command or Invoke-Expression"
        Read-Host -Prompt "Installation was not successful, press Enter to exit"
        Exit 1
    }
}

$IDEADevMode = if ($Env:RES_DEV_MODE) {$Env:RES_DEV_MODE} else {""}
$VirtualEnv = if ($Env:VIRTUAL_ENV) {$Env:VIRTUAL_ENV} else {""}
$ScriptDir = $PSScriptRoot
$IDEARevision = if ($Env:IDEA_REVISION) {$Env:IDEA_REVISION} else {"v2023.10"}
$IDEADockerRepo = "public.ecr.aws/g8j8s8q8"
$DocumentationError = "https://ide-on-aws.com"
$AWSProfile = if ($Env:AWS_PROFILE) {$Env:AWS_PROFILE} else {"default"}
$AWSRegion= if ($Env:AWS_REGION) {$Env:AWS_REGION} else {"us-east-1"}
Set-Location -Path "${ScriptDir}"


if ($IDEADevMode -ne "") {
    if (Test-Path -Path "${ScriptDir}/RES_VERSION.txt") {
        $IDEADevMode="true"
    }
    else {
        $IDEADevMode="false"
    }
}

if ($IDEADevMode -eq "true") {
    Write-Host "Development Mode is only supported on Linux/Mac"
    <#
    if ($VirtualEnv -eq "") {
        if (Test-Path -Path "$ScriptDir/venv") {
            . "$ScriptDir/venv/bin/activate"
        }
        else {
            Verify-Command "Get-Command" "Python Virtual Environment not detected. Install virtual environment to execute res-admin.sh in dev mode." "source ${ScriptDir}/venv/bin/activate"
        }
    }
    IDEA_SKIP_WEB_BUILD=${IDEA_SKIP_WEB_BUILD:-'0'}
    $IDESkipWebBuild = if (IDEA_SKIP_WEB_BUILD) {$Env:RES_DEV_MODE} else {""}
    TOKENS=$(echo $(printf ",\"%s\"" "${@}"))
    TOKENS=${TOKENS:1}
    ARGS=$(echo "[${TOKENS}]" | base64)
    CMD="invoke cli.admin --args=${ARGS}"
    IDEA_SKIP_WEB_BUILD=${IDEA_SKIP_WEB_BUILD} eval $CMD
    exit $? #>
}

$DockerBin=$(Get-Command docker).source 2>$null
Verify-Command "Get-Command" "Docker not detected. Download and install it from https://docs.docker.com/get-docker/. Read the Docker Subscription Service Agreement first (https://www.docker.com/legal/docker-subscription-service-agreement/)." "Get-Command docker"

$AWSCliBin=$(Get-Command aws).source 2>$null
Verify-Command "Get-Command" "awscli not detected. Download and install it from https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" "Get-Command aws"

if (-not (Test-Path "$HOME/.idea/clusters") ) {
    New-Item -ItemType "directory" -Path "$HOME/.idea/clusters" | Out-Null
}

Invoke-Expression "& '$DockerBin' version" | Out-Null 2>$null
Verify-Command "Invoke-Expression" "Docker is installed on the system but it does not seems to be running. Start Docker first." "docker info"

[System.Net.Dns]::GetHostEntry("public.ecr.aws") 2>$null | Out-Null
Verify-Command "Get-Command" "Unable to query ECR. Are you connected to internet?" "[System.Net.Dns]::GetHostEntry($IDEADockerRepo)"

# Select-String -Quiet does not work properly if the number of Docker images is 0, so we go old school and verify if the variable is empty
$ImageExist = Invoke-Expression "& '$DockerBin' images" | Select-String "$IDEADockerRepo/idea-administrator" | Select-String "$IDEARevision"
if ($ImageExist -eq $null) {
    Invoke-Expression "& '$DockerBin' pull $IDEADockerRepo/idea-administrator:$IDEARevision"
    Verify-Command "Invoke-Expression" "Unable to download IDEA container image. Refer to the error above. If your token has expired, run:  docker logout public.ecr.aws" "$DockerBin pull $IDEADockerRepo/idea-administrator:$IDEARevision"
}

if ($args.count -eq 0) {
    $args = "quick-setup"
    Write-Host "No arguments detected, defaulting to quick-setup. Use -h to see all options."
}

Invoke-Expression "& '$DockerBin' run --rm -it -v $HOME/.idea/clusters:/root/.idea/clusters -v $HOME/.aws:/root/.aws $IDEADockerRepo/idea-administrator:$IDEARevision idea-admin $args"

Read-Host -Prompt "Press Enter to exit"
