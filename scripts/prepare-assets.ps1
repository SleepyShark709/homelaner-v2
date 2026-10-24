param([switch]$ReuseExports, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
  if (-not $ReuseExports) {
    & $Python tools/asset-pipeline/export_samples.py
    if ($LASTEXITCODE -ne 0) { throw 'Original asset export failed.' }
  }
  & $Python tools/asset-pipeline/publish_original.py
  if ($LASTEXITCODE -ne 0) { throw 'Mesh publication failed.' }
  & $Python scripts/convert-original-animations.py
  if ($LASTEXITCODE -ne 0) { throw 'Animation conversion failed.' }
  & $Python scripts/assemble-original-character.py
  if ($LASTEXITCODE -ne 0) { throw 'Character assembly failed.' }
  & $Python scripts/prepare-citizen.py
  if ($LASTEXITCODE -ne 0) { throw 'Original citizen/combat source preparation failed.' }
  & $Python scripts/attach-combat-animations.py
  if ($LASTEXITCODE -ne 0) { throw 'Combat animation attachment failed.' }
  & $Python tools/asset-pipeline/export-city.py
  if ($LASTEXITCODE -ne 0) { throw 'Original district reconstruction failed.' }
  & $Python tools/asset-pipeline/export-routes.py
  if ($LASTEXITCODE -ne 0) { throw 'Original geometry route preparation failed.' }
  & $Python tools/asset-pipeline/export-population.py
  if ($LASTEXITCODE -ne 0) { throw 'Population model/placement preparation failed.' }
  $catalogPath = Join-Path $projectRoot 'public/assets/original/catalog.json'
  $entries = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $hero = $entries | Where-Object id -eq 'hero'
  $hero.url = '/assets/character/hero.gltf'
  $hero.notes = '原版主角身体93骨骼、头发和墨镜各2骨骼，共97骨骼；保留原版移动与战斗动作和蒙皮。附件按原head_accessories挂点装配，材质仍为简化PBR。'
  $json = ConvertTo-Json -InputObject @($entries) -Depth 20
  [System.IO.File]::WriteAllText($catalogPath, $json, [System.Text.UTF8Encoding]::new($false))
  Write-Host 'Original character, combat, district and 14 population assets ready. Run node scripts/verify-assets.mjs --game.'
} finally { Pop-Location }
