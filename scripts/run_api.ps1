$ErrorActionPreference = 'Stop'
Set-Location 'I:\Company'
New-Item -ItemType Directory -Force 'I:\Company\logs' | Out-Null
$python = 'I:\Company\.venv\Scripts\python.exe'
$log = 'I:\Company\logs\api.log'
"[$(Get-Date -Format o)] starting API" | Out-File -FilePath $log -Append -Encoding utf8
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 *>> $log
