$ErrorActionPreference = 'Stop'
$root = 'I:\Company'
$python = "$root\.venv\Scripts\python.exe"
$user = "$env:USERDOMAIN\$env:USERNAME"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$api = New-ScheduledTaskAction -Execute $python -Argument '-m uvicorn app.main:app --host 127.0.0.1 --port 8765' -WorkingDirectory $root
$worker = New-ScheduledTaskAction -Execute $python -Argument '-m app.worker' -WorkingDirectory $root
$company = New-ScheduledTaskAction -Execute $python -Argument '-m app.company_worker' -WorkingDirectory $root
Register-ScheduledTask -TaskName 'AgentCompany-API' -Action $api -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Register-ScheduledTask -TaskName 'AgentCompany-Worker' -Action $worker -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Register-ScheduledTask -TaskName 'AgentCompany-Loop' -Action $company -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Output 'Agent Company API, coding worker, and company loop startup tasks installed.'