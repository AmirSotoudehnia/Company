$ErrorActionPreference = 'SilentlyContinue'
$apiTask = Get-ScheduledTask -TaskName 'AgentCompany-API'
$workerTask = Get-ScheduledTask -TaskName 'AgentCompany-Worker'
Write-Output "API task: $($apiTask.State)"
Write-Output "Worker task: $($workerTask.State)"
try {
    $response = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8765/control' -TimeoutSec 5
    Write-Output "Control panel HTTP: $($response.StatusCode)"
} catch { Write-Output 'Control panel HTTP: DOWN' }
$workers = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*-m app.worker*' }
$apis = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*uvicorn app.main:app*' }
Write-Output "Worker process chain count: $($workers.Count)"
Write-Output "API process chain count: $($apis.Count)"
Write-Output "C free GB: $([math]::Round((Get-PSDrive C).Free / 1GB, 2))"