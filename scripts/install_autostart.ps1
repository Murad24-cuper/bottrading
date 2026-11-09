$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $projectRoot 'start_bot.bat'
if (-not (Test-Path -LiteralPath $startScript)) { throw "Missing start_bot.bat: $startScript" }
$taskName = 'XMTradingBotSupervisor'
$userId = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute $startScript -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -DisallowStartIfOnBatteries:$false -StopIfGoingOnBatteries:$false
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Start the local DEMO trading bot supervisor at user logon.' -Force | Out-Null
Write-Output "Scheduled task registered: $taskName (current user, logon trigger)."
