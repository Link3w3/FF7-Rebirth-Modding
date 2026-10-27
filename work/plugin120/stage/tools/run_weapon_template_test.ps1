# The weapon Blueprint Maker's test (Create a Character System editor 1.20), run by run_build_editor120.cmd after the
# build (the End editor closed): writes Saved\RebirthSkelCompat\WeaponTemplate\job.json and runs
# weapon\build_weapon_test.py in an editor commandlet. The jobs:
#   - Seraph Sephiroth's weapon: the game's playable (cut-scale) Masamune's template holding the Essence Shard, made at
#     /Game/BluePrint/Character/Weapon/WE1021_15_Essence_Shard/WE1021_10_SephirothIllusion_MasamuneCutScale (the class the
#     Seraph skins' Weapon names), then cooked alone into the test container weapon\out\CACS_WeaponTemplateTest_P (NOT
#     installed: Sandalphon checks it);
#   - three more made and compiled only (/Game/RebirthSkelCompat/WeaponTemplateTest): Cloud's Buster Sword's template
#     holding the Kingdom Key (its collision settings), a security soldier's gun's holding Vincent's Quicksilver (its
#     cartridge component), Tifa's gloves' (the sync-pose weapon class) holding the Kingdom Key.
# A test asset made before is moved aside first (to C:\FF7R2UProj\_mod_backups\weapon_test_before_<time>\); the Seraph
# weapon is only made when it is not there yet.
# Exit 0: every job made (and the cook done); 1 otherwise. Log: build\weapon_template_editor.log.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'editor120_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'weapon\build_weapon_test.py'
$Saved = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\WeaponTemplate'
$Job = Join-Path $Saved 'job.json'
$Result = Join-Path $Saved 'result.json'
$Log = Join-Path $Build 'weapon_template_editor.log'
$Out = Join-Path $Here 'weapon\out'
try {
    New-Item -ItemType Directory -Force -Path $Saved | Out-Null
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    $Content = 'C:\FF7R2UProj\Content'
    $Jobs = @()
    $Seraph = '/Game/BluePrint/Character/Weapon/WE1021_15_Essence_Shard/WE1021_10_SephirothIllusion_MasamuneCutScale'
    $SeraphFile = Join-Path $Content ($Seraph.Substring(6).Replace('/', '\') + '.uasset')
    if (Test-Path $SeraphFile) {
        Say ('   Seraph weapon Blueprint already in the project (' + $SeraphFile + '): not made again; cooked only')
        $Jobs += @{ template = 'none'; mesh = ''; package = $Seraph; replace = $false; cook_only = $true;
                    container = 'CACS_WeaponTemplateTest_P'; out = $Out }
    } else {
        $Jobs += @{ template = 'WE1021_10_SephirothIllusion_MasamuneCutScale'; mesh = '/Game/Character/Weapon/WE1021_15_Essence_Shard/Model/WE001021_15';
                    package = $Seraph; replace = $false; container = 'CACS_WeaponTemplateTest_P'; out = $Out }
    }
    $Tests = @(
        @{ template = 'WE0000_00_Cloud_BusterSword'; mesh = '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00';
           package = '/Game/RebirthSkelCompat/WeaponTemplateTest/WE0000_00_Cloud_BusterSword'; replace = $false },
        @{ template = 'WE1000_00_SecuritySoldier_Gun'; mesh = '/Game/Character/Weapon/WE0011_00_Vincent_Quiksilver/Model/WE0011_00';
           package = '/Game/RebirthSkelCompat/WeaponTemplateTest/WE1000_00_SecuritySoldier_Gun'; replace = $false },
        @{ template = 'WE0002_00_Tifa_LeatherGlove'; mesh = '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00';
           package = '/Game/RebirthSkelCompat/WeaponTemplateTest/WE0002_00_Tifa_LeatherGlove'; replace = $false }
    )
    $Aside = Join-Path 'C:\FF7R2UProj\_mod_backups' ('weapon_test_before_{0:yyyyMMdd_HHmmss}' -f (Get-Date))
    foreach ($J in $Tests) {
        $Rel = $J.package.Substring(6).Replace('/', '\') + '.uasset'
        $File = Join-Path $Content $Rel
        if (Test-Path $File) {
            $To = Join-Path $Aside $Rel
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $To) | Out-Null
            Move-Item -Force -Path $File -Destination $To
            Say ('   the one made before moved aside: Content\' + $Rel + ' -> ' + $To)
        }
        $Jobs += $J
    }
    $Text = @{ jobs = $Jobs } | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($Job, $Text, (New-Object System.Text.UTF8Encoding($false)))
    if (Test-Path $Result) { Remove-Item -Force $Result }
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('weapon_template_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
    $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(45)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Now = Get-Content -Raw -Path $Result
            if ($Now -match '"done"' -or $Now -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 45 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no result file from the editor (build\weapon_template_editor.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    Say ('   ' + $Json.templates + ' weapon templates read')
    $Ok = $true
    foreach ($Entry in $Json.jobs) {
        $M = $Entry.made
        if ($null -eq $M) { Say ('   ' + $Entry.job.template + ': stopped before it was made'); $Ok = $false; continue }
        Say ('   {0} -> {1}: {2} (compile: {3}; {4} default(s), {5} setting(s), {6} component(s); {7} error(s), {8} warning(s), {9} compiler message(s))' -f
             $Entry.job.template, $Entry.job.package, $(if ($M.ok) { 'MADE' } else { 'NOT MADE' }), $M.compile, $M.defaults, $M.settings, $M.components,
             @($M.errors).Count, @($M.warnings).Count, @($M.compiler).Count)
        foreach ($E in @($M.errors) | Select-Object -First 5) { Say ('      ERROR: ' + $E) }
        foreach ($E in @($M.compiler) | Select-Object -First 5) { Say ('      compiler: ' + $E) }
        foreach ($E in @($M.warnings) | Select-Object -First 5) { Say ('      warning: ' + $E) }
        if (-not $M.ok) { $Ok = $false }
        if ($Entry.job.container) {
            $C = $Entry.cooked
            if ($null -eq $C) { Say '      NOT cooked'; $Ok = $false }
            elseif (-not $C.ok) { Say ('      NOT cooked: ' + (@($C.errors) -join ' / ')); $Ok = $false }
            else { Say ('      cooked into weapon\out\' + $Entry.job.container + ' (not installed)') }
        }
    }
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR in the editor script: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); $Ok = $false }
    if ($Ok) { exit 0 } else { exit 1 }
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
