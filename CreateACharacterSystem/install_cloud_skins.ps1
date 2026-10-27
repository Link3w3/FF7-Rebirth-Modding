# Installs the Cloud skins: skins\RemakeCloud (Remake Cloud) and skins\RebirthCloud (Cloud (Rebirth)), and the skins
# container (~mods\CreateACharacterSkins_P) made from every skin installed on 2026-10-26 plus those two.
# Run it with the game closed, through install_cloud_skins.cmd (next to this file).
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$stage = Join-Path $here 'stage_cloudskins'
$status = Join-Path $here 'install_cloud_skins_status.txt'
Set-Content -LiteralPath $status -Value ('started ' + (Get-Date -Format 's')) -Encoding UTF8
function Say([string]$Text) { Write-Host $Text; Add-Content -LiteralPath $status -Value $Text -Encoding UTF8 }
function Md5([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm MD5).Hash.ToLowerInvariant() }

$game = 'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
$mod  = Join-Path $game 'End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat'
$mods = Join-Path $game 'End\Content\Paks\~mods'
$back = Join-Path $game '_mod_backups\cloudskins_20261026\container_before'
$names = @('CreateACharacterSkins_P.utoc', 'CreateACharacterSkins_P.ucas', 'CreateACharacterSkins_P.pak')
$old = @{ 'CreateACharacterSkins_P.utoc' = 'b8739d08f077092662ce9c25b0d9f744'; 'CreateACharacterSkins_P.ucas' = '1c1043b251064a6adfe05ef0011c4c69'; 'CreateACharacterSkins_P.pak' = '602a1b0aee4bf950ec7a27d6bacae32e' }
$new = @{ 'CreateACharacterSkins_P.utoc' = '094ba9a716454ecf489c2e8a9b490b37'; 'CreateACharacterSkins_P.ucas' = '506911ef1ef154098eef0dbf6fdaa9bf'; 'CreateACharacterSkins_P.pak' = '602a1b0aee4bf950ec7a27d6bacae32e' }
$skinFiles = [ordered]@{
  'RebirthCloud\skin.json' = '61bf8b602be75f8d040a1df79a8bfad4'
  'RemakeCloud\Content\GameContents\Character\Player\PC0000_00_Cloud_Standard\Model\PC0000_00.uasset' = '1407349cc98bb56b48fed2bb27123e9a'
  'RemakeCloud\Content\GameContents\Character\Player\PC0000_00_Cloud_Standard\Model\PC0000_00_BNM.uasset' = '05b4bb4b5bfe64c26c086f66903e6861'
  'RemakeCloud\Content\GameContents\Character\Player\PC0000_00_Cloud_Standard\Model\PC0000_00_Skeleton.uasset' = 'b0623c779dde79f13267b9db8ba43408'
  'RemakeCloud\skin.json' = '9e4fb6971ae59dc709553a51b67ee995'
}
$replaced = $false
try {
  $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -ieq 'ff7rebirth_' -or $_.ProcessName -ieq 'ff7rebirth' })
  if ($running.Count -gt 0) { Say 'NOT installed: FINAL FANTASY VII REBIRTH is running. Close it, then run install_cloud_skins.cmd again.'; exit 1 }
  if (-not (Test-Path -LiteralPath (Join-Path $mod 'skins'))) { Say ('NOT installed: there is no ' + (Join-Path $mod 'skins')); exit 1 }
  # the staged files, as they were made
  foreach ($n in $names) {
    $p = Join-Path $stage ('container\' + $n)
    if ((Md5 $p) -ne $new[$n]) { Say ('NOT installed: the staged ' + $n + ' is not the one made (' + $p + ')'); exit 1 }
  }
  foreach ($f in $skinFiles.Keys) {
    $p = Join-Path $stage ('skins\' + $f)
    if ((Md5 $p) -ne $skinFiles[$f]) { Say ('NOT installed: the staged skins\' + $f + ' is not the one made'); exit 1 }
  }
  # the installed container must be the one the new one was made from (or the new one, from an earlier run)
  foreach ($n in $names) {
    $p = Join-Path $mods $n
    if (-not (Test-Path -LiteralPath $p)) { Say ('NOT installed: ' + $p + ' is missing'); exit 1 }
    $h = Md5 $p
    if ($h -ne $old[$n] -and $h -ne $new[$n]) {
      Say ('NOT installed: ~mods\' + $n + ' changed after the new container was made (a skin was built or installed since). Ask Sandalphon to make the container again.')
      exit 1
    }
  }
  if (-not (Test-Path -LiteralPath (Join-Path $mods 'RebirthGameMaterials_P.utoc'))) {
    Say 'Note: ~mods\RebirthGameMaterials_P is not installed: Remake Cloud shows the default material until it is.'
  }
  # the container as it was (once: running this again keeps the first copy)
  New-Item -ItemType Directory -Force -Path $back | Out-Null
  foreach ($n in $names) {
    $b = Join-Path $back $n
    if (-not (Test-Path -LiteralPath $b)) {
      Copy-Item -LiteralPath (Join-Path $mods $n) -Destination $b
      if ((Md5 $b) -ne (Md5 (Join-Path $mods $n))) { throw ('the copy of ' + $n + ' in ' + $back + ' is not the same') }
    }
  }
  # the skin folders
  foreach ($f in $skinFiles.Keys) {
    $to = Join-Path (Join-Path $mod 'skins') $f
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
    Copy-Item -LiteralPath (Join-Path $stage ('skins\' + $f)) -Destination $to -Force
    if ((Md5 $to) -ne $skinFiles[$f]) { throw ('skins\' + $f + ' did not copy') }
  }
  Say 'Skins: skins\RebirthCloud (Cloud (Rebirth)) and skins\RemakeCloud (Remake Cloud) are installed.'
  # the container
  $replaced = $true
  foreach ($n in $names) {
    Copy-Item -LiteralPath (Join-Path $stage ('container\' + $n)) -Destination (Join-Path $mods $n) -Force
  }
  foreach ($n in $names) {
    if ((Md5 (Join-Path $mods $n)) -ne $new[$n]) { throw ($n + ' did not copy') }
  }
  Say ('Skins container: ~mods\CreateACharacterSkins_P, 98 packages (the 95 before and Remake Cloud''s 3). The one before is in ' + $back)
  Say 'OK. Start the game, then Customization > SKINS on Cloud: Cloud (Rebirth) or Remake Cloud.'
  exit 0
} catch {
  Say ('FAILED: ' + $_.Exception.Message)
  if ($replaced) {
    try {
      foreach ($n in $names) { Copy-Item -LiteralPath (Join-Path $back $n) -Destination (Join-Path $mods $n) -Force }
      Say ('The container from before is back (from ' + $back + ').')
    } catch {
      Say ('Could not put the container from before back: ' + $_.Exception.Message + ' (it is in ' + $back + ')')
    }
  }
  exit 1
}
