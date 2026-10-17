# Registers Lobo's heartbeat as a Windows scheduled task that starts when you
# log in and runs hidden. No admin needed.
#
#   .\scripts\install-task.ps1            install (or update) the task
#   .\scripts\install-task.ps1 -Remove    uninstall it
#
# Start/stop it by hand:  Start-ScheduledTask "Lobo heartbeat"
#                         Stop-ScheduledTask  "Lobo heartbeat"
# Its output goes to home\heartbeat.log.
param(
    [switch]$Remove,
    [string]$Pythonw = (Join-Path (Split-Path (Get-Command python).Source) "pythonw.exe")
)

$TaskName = "Lobo heartbeat"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed '$TaskName'."
    return
}

$repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path $Pythonw)) { throw "pythonw.exe not found at $Pythonw" }

# pythonw runs without a console window. The working directory is the repo so
# `-m lobo.heartbeat` finds the package. The DeepSeek key comes from your user
# environment variables, which a task running as you inherits at login.
$action = New-ScheduledTaskAction -Execute $Pythonw `
    -Argument "-X utf8 -m lobo.heartbeat --log --scheduled" -WorkingDirectory $repo

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

# ExecutionTimeLimit 0 = never kill it (the default is 72 hours). IgnoreNew means
# a second copy is never started. Restart: if it dies at startup, retry 3 times.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Force `
    -Description "Lobo's heartbeat: wakes the agent on the schedule it chooses." | Out-Null

Write-Host "Installed '$TaskName'. It starts at your next login."
Write-Host "Start it now with:  Start-ScheduledTask '$TaskName'"
