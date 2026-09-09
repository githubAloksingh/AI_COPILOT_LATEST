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

& $python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
