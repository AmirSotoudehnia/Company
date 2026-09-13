$ErrorActionPreference = 'Stop'
Set-Location 'I:\Company'
New-Item -ItemType Directory -Force 'I:\Company\logs' | Out-Null
$python = 'I:\Company\.venv\Scripts\python.exe'
$log = 'I:\Company\logs\worker.log'
"[$(Get-Date -Format o)] starting worker" | Out-File -FilePath $log -Append -Encoding utf8
& $python -m app.worker *>> $log
