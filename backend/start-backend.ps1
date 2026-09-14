$ErrorActionPreference = 'Stop'

$envFile = Join-Path $PSScriptRoot '..\.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}

$existingListener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    try {
        $health = Invoke-RestMethod 'http://localhost:8080/api/health' -TimeoutSec 3
        if ($health.service -eq 'AI Work Copilot' -and $health.status -eq 'UP') {
            Write-Host 'Backend is already running and healthy at http://localhost:8080.'
            exit 0
        }
    } catch {
        throw 'Port 8080 is already in use by another process. Stop that process or configure a different backend port.'
    }
}

$localMaven = Join-Path $PSScriptRoot '.tools\apache-maven-3.9.9\bin\mvn.cmd'
if (Test-Path $localMaven) {
    & $localMaven spring-boot:run -DskipTests
    exit $LASTEXITCODE
}

if (Get-Command mvn -ErrorAction SilentlyContinue) {
    mvn spring-boot:run -DskipTests
    exit $LASTEXITCODE
}

throw 'Apache Maven is unavailable. Run the setup again or install Maven.'
