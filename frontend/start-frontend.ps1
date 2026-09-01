$ErrorActionPreference = 'Stop'

$localNodeDir = Join-Path $PSScriptRoot '.tools\node-v24.19.0-win-x64'
if (Test-Path $localNodeDir) {
    $env:PATH = "$localNodeDir;" + $env:PATH
}

npx ng serve --port 4200
