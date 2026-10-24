$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$systemNode = Get-Command node -ErrorAction SilentlyContinue
$nodeCommand = if (Test-Path -LiteralPath $bundledNode) { $bundledNode } elseif ($systemNode) { $systemNode.Source } else { throw 'Node.js >=22.12 is required.' }
$env:PATH = (Split-Path -Parent $nodeCommand) + ';' + $env:PATH
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath 'node_modules\vite\bin\vite.js')) { throw 'Dependencies are missing. Run npm install with Node >=22.12 first.' }
& $nodeCommand 'node_modules\vite\bin\vite.js' --host 127.0.0.1 --port 5178 --strictPort
exit $LASTEXITCODE
