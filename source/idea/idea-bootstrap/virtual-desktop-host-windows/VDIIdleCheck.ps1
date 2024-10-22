param (
    [Parameter(Mandatory = $true)]
    [string]$AWSRegion,

    [Parameter(Mandatory = $true)]
    [string]$ENVName
)

$timestamp = Get-Date -Format 'yyyyMMddTHHmmssffffZ'
$RESIdleCheckVDI =  "$env:SystemDrive\IDEA\Logs\RESIdleCheckVDI\VDIIdleCheck.log.$timestamp"
$IdleConfigFile = "C:\IDEA\Idle_Config.json"

Start-Transcript -Path $RESIdleCheckVDI -NoClobber -IncludeInvocationHeader

Write-Host "AWSRegion = $AWSRegion"
Write-Host "ENVName = $ENVName"

function Get-Cluster-Settings {
    Param(
        [string]$key
    )
    aws dynamodb get-item `
    --region $AWSRegion `
    --table-name "$ENVName.cluster-settings" `
    --key "{\""key\"": {\""S\"": \""$key\""}}" `
    --output text `
    --query 'Item.value.S || Item.value.N'
}

function VDI-Idle-Check {

    if (-not (Test-Path $IdleConfigFile)) {

        $CPU_UTILIZATION_THRESHOLD=Get-Cluster-Settings("vdc.dcv_session.cpu_utilization_threshold")
        $IDLE_TIMEOUT=Get-Cluster-Settings("vdc.dcv_session.idle_timeout")
        $VDI_HELPER_API_URL=Get-Cluster-Settings("vdc.vdi_helper_api_gateway_url")
        $TRANSITION_STATE=Get-Cluster-Settings("vdc.dcv_session.transition_state")

        $IdleConfigObject = [PSCustomObject]@{
            idle_cpu_threshold = $CPU_UTILIZATION_THRESHOLD
            idle_timeout = $IDLE_TIMEOUT
            vdi_helper_api_url = $VDI_HELPER_API_URL
            transition_state = $TRANSITION_STATE
        }

        $IdleConfigObject | ConvertTo-Json | Set-Content -Path $IdleConfigFile -Encoding UTF8
    }

    $IdleConfig = Get-Content -Path $IdleConfigFile -Raw | ConvertFrom-Json

    $CPU_UTILIZATION_THRESHOLD = $IdleConfig.idle_cpu_threshold
    $IDLE_TIMEOUT = $IdleConfig.idle_timeout
    $VDI_HELPER_API_URL = $IdleConfig.vdi_helper_api_url
    $TRANSITION_STATE = $IdleConfig.transition_state

    Write-Host "CPU_UTILIZATION_THRESHOLD = $CPU_UTILIZATION_THRESHOLD"
    Write-Host "IDLE_TIMEOUT = $IDLE_TIMEOUT"
    Write-Host "VDI_HELPER_API_URL = $VDI_HELPER_API_URL"
    Write-Host "TRANSITION_STATE = $TRANSITION_STATE"

    $VDIAutoStopScriptPath = "$env:SystemDrive\Users\Administrator\RES\Bootstrap\vdi-helper\vdi_auto_stop.py"

    Write-Host "VDIAutoStopScriptPath = $VDIAutoStopScriptPath"

    Stop-Transcript

    python "$VDIAutoStopScriptPath" `
    --aws-region "$AWSRegion" `
    --api-url "$VDI_HELPER_API_URL" `
    --log-file "$RESIdleCheckVDI" `
    --cpu-threshold "$CPU_UTILIZATION_THRESHOLD" `
    --idle-timeout "$IDLE_TIMEOUT" `
    --transition-state "$TRANSITION_STATE" `
    --uptime-minimum 5  # Avoid stopping the instance immediately after booting up
}

VDI-Idle-Check

