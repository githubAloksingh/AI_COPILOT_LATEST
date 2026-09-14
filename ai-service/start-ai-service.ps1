$ErrorActionPreference = 'Stop'

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Creating AI service virtual environment...'
    py -m venv (Join-Path $PSScriptRoot '.venv')
}

if (-not (Test-Path $python)) {
    throw "Could not find Python virtual environment at $python"
}

$envFile = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path $envFile)) {
    $rootEnv = Join-Path $PSScriptRoot '..\.env'
    if (Test-Path $rootEnv) {
        $envFile = $rootEnv
    }
}

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}

$env:HF_HUB_DISABLE_XET = '1'

$existingListener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    try {
        $health = Invoke-RestMethod 'http://localhost:8000/health' -TimeoutSec 3
        if ($health.service -eq 'ai-service' -and $health.status -eq 'healthy') {
            Write-Host 'AI service is already running and healthy at http://localhost:8000.'
            exit 0
        }
    } catch {
        throw 'Port 8000 is already in use by another process. Stop that process or configure a different AI service port.'
    }
}

& $python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
