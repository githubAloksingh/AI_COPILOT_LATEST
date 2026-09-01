$ErrorActionPreference = 'Stop'

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

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
