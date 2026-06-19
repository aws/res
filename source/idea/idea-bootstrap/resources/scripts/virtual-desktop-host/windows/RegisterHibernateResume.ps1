#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Register a scheduled task that restarts the VDI app when the system resumes from hibernation.
# On resume, the existing VDIAppRestartNotification task is re-triggered so that
# the virtual-desktop-app reruns its post_reboot logic and updates the VDI session state.

$trigger = New-CimInstance -Namespace "Root/Microsoft/Windows/TaskScheduler" `
    -ClassName MSFT_TaskEventTrigger -ClientOnly -Property @{
        Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name="Microsoft-Windows-Kernel-Power"] and EventID=107]]</Select></Query></QueryList>'
        Enabled = $True
    }
$trigger.PSObject.TypeNames.Insert(0, "Microsoft.Management.Infrastructure.CimInstance#MSFT_TaskTrigger")

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-Command "Write-Host \"System resumed from hibernation, restarting virtual-desktop-app\"; Stop-Process -Name resserver -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; schtasks /run /tn VDIAppRestartNotification"'

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName "RESHibernateResume" -Action $action -Trigger $trigger -Principal $principal -Force
