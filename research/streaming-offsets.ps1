param([string]$Source, [string]$Output)
$ErrorActionPreference='Stop'
$streamAsm=[System.Reflection.Assembly]::LoadFrom('E:/undefeated-web/tools/asset-pipeline/uasset-net472/UAssetGUI.exe')
foreach($streamResource in @('costura.newtonsoft.json.dll.compressed','costura.uassetapi.dll.compressed')) {
  $streamInput=$streamAsm.GetManifestResourceStream($streamResource)
  $streamDeflate=[System.IO.Compression.DeflateStream]::new($streamInput,[System.IO.Compression.CompressionMode]::Decompress)
  $streamMemory=[System.IO.MemoryStream]::new();$streamDeflate.CopyTo($streamMemory)
  $null=[System.Reflection.Assembly]::Load($streamMemory.ToArray())
}
$streamAsset=[UAssetAPI.UAsset]::DeserializeJson([System.IO.File]::ReadAllText($Source))
[UAssetAPI.Kismet.KismetSerializer]::asset=$streamAsset
$streamRecords=@()
for($streamEi=0;$streamEi -lt $streamAsset.Exports.Count;$streamEi++) {
 $streamExport=$streamAsset.Exports[$streamEi]
 if($streamExport -isnot [UAssetAPI.ExportTypes.FunctionExport]) { continue }
 [int]$streamOffset=0;$streamStmts=@()
 for($streamSi=0;$streamSi -lt $streamExport.ScriptBytecode.Length;$streamSi++) {
   $streamBefore=$streamOffset
   $streamProjected=[UAssetAPI.Kismet.KismetSerializer]::SerializeExpression($streamExport.ScriptBytecode[$streamSi],[ref]$streamOffset,$true)
   $streamStmts+=@{index=$streamSi;offset=$streamBefore;endOffset=$streamOffset;projection=$streamProjected.ToString()}
 }
 $streamRecords+=@{exportIndex=$streamEi;function=$streamExport.ObjectName.ToString();computedSize=$streamOffset;declaredSize=$streamExport.ScriptBytecodeSize;statements=$streamStmts}
}
$streamRecords | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $Output -Encoding utf8
Write-Output ($streamRecords | Select-Object function,computedSize,declaredSize | ConvertTo-Json -Compress)
