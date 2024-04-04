function Export-EnvironmentVariables {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$ProjectId,

        [Parameter(Mandatory = $true)]
        [string]$OwnerId,

        [Parameter(Mandatory = $true)]
        [string]$ProjectName,

        [Parameter(Mandatory = $true)]
        [string]$EnvName,

        [Parameter(Mandatory = $true)]
        [string]$OnVDIStartCommands,

        [Parameter(Mandatory = $true)]
        [string]$OnVDIConfigureCommands

    )

    $StoragePath = ".\environment_variables.json"
    $envVariables = [PSCustomObject]@{
        ProjectId = $ProjectId
        OwnerId = $OwnerId
        EnvName = $EnvName
        ProjectName = $ProjectName
        OnVDIStartCommands = $OnVDIStartCommands
        OnVDIConfigureCommands = $OnVDIConfigureCommands
    }

    $envVariables | ConvertTo-Json | Set-Content -Path $StoragePath -Encoding UTF8

    # Set environment variables
    $env:PROJECT_ID = $ProjectId
    $env:OWNER_ID = $OwnerId
    $env:ENV_NAME = $EnvName
    $env:PROJECT_NAME = $ProjectName
    $env:ON_VDI_START_COMMANDS = $OnVDIStartCommands
    $env:ON_VDI_CONFIGURED_COMMANDS = $OnVDIConfigureCommands

    Write-Host "Environment variables have been set:"
    Write-Host "PROJECT_ID = $env:PROJECT_ID"
    Write-Host "OWNER_ID = $env:OWNER_ID"
    Write-Host "ENV_NAME = $env:ENV_NAME"
    Write-Host "ON_VDI_START_COMMANDS = $env:ON_VDI_START_COMMANDS"
    Write-Host "ON_VDI_CONFIGURED_COMMANDS = $env:ON_VDI_CONFIGURED_COMMANDS"
    Write-Host "PROJECT_NAME = $env:PROJECT_NAME"
}
