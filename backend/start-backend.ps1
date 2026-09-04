$ErrorActionPreference = 'Stop'

$envFile = Join-Path $PSScriptRoot '..\.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
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
