# RebirthSkelCompat: finds the game's recent crash reports and copies them into -Dest.
# Read-only everywhere except -Dest.
param([string]$Dest)
$ErrorActionPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$since = (Get-Date).AddDays(-2)
"=== Now: " + (Get-Date).ToString('s')
"=== Application event log entries about ff7rebirth since " + $since.ToString('s')
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$since} -ErrorAction SilentlyContinue |
  Where-Object { ($_.Id -in 1000,1001,1002,1005,1026) -and ($_.Message -match 'ff7rebirth') } |
  Sort-Object TimeCreated |
  ForEach-Object { "--- {0}  Id {1}  {2}" -f $_.TimeCreated.ToString('s'), $_.Id, $_.ProviderName; $_.Message }
"=== Unreal crash folders (CrashContext.runtime-xml), all dates"
$roots = @($env:LOCALAPPDATA, [Environment]::GetFolderPath('MyDocuments'), (Join-Path $env:USERPROFILE 'Saved Games'), $env:APPDATA)
foreach ($r in $roots) {
  if (-not $r -or -not (Test-Path -LiteralPath $r)) { continue }
  Get-ChildItem -LiteralPath $r -Recurse -Depth 6 -Force -Filter 'CrashContext.runtime-xml' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime |
    ForEach-Object {
      "{0}  {1}" -f $_.LastWriteTime.ToString('s'), $_.FullName
      if ($_.LastWriteTime -gt $since) {
        $target = Join-Path $Dest $_.Directory.Name
        Copy-Item -LiteralPath $_.Directory.FullName -Destination $target -Recurse -Force
        "    copied to $target"
      }
    }
}
"=== Windows Error Reporting reports for ff7rebirth since " + $since.ToString('s')
foreach ($w in @((Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\WER'), (Join-Path $env:ProgramData 'Microsoft\Windows\WER'))) {
  Get-ChildItem -LiteralPath $w -Recurse -Depth 3 -Force -Filter 'Report.wer' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $since -and $_.Directory.Name -match 'ff7rebirth' } |
    ForEach-Object {
      "{0}  {1}" -f $_.LastWriteTime.ToString('s'), $_.FullName
      $target = Join-Path $Dest ('WER_' + $_.Directory.Name)
      New-Item -ItemType Directory -Force -Path $target | Out-Null
      Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
}
"=== CrashDumps since " + $since.ToString('s')
Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'CrashDumps') -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt $since } |
  ForEach-Object { "{0}  {1}  {2}" -f $_.LastWriteTime.ToString('s'), $_.Length, $_.FullName }
"=== done"
