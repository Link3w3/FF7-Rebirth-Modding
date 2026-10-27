# The editable AnimBlueprints' test (Create a Character System editor 1.19), run by run_build_editor119.cmd after the
# build (the End editor closed): writes Saved\RebirthSkelCompat\AnimTemplate\job.json and runs build_abp_template.py in
# an editor commandlet. The jobs: Cloud's template rebuilt for Cloud's own skeleton at his AnimBlueprint's own path, then
# cooked into the test container CACS_AnimTemplateTest_P (Tools\RebirthSkelCompat\abp\out; installed only by
# run_abp_template_test_install.cmd); Sephiroth's and Vincent's templates for their skeletons and the monsters' for
# Cloud's (/Game/RebirthSkelCompat/AnimTemplateTest), made and compiled only.
# Exit 0: every job made (and the cook done); 1 otherwise. Log: build\abp_template_editor.log.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'editor119_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'abp\build_abp_template.py'
$Saved = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\AnimTemplate'
$Job = Join-Path $Saved 'job.json'
$Result = Join-Path $Saved 'result.json'
$Log = Join-Path $Build 'abp_template_editor.log'
$Out = Join-Path $Here 'abp\out'
try {
    New-Item -ItemType Directory -Force -Path $Saved | Out-Null
    $Jobs = @(
        @{ template = 'cloud'; skeleton = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton';
           package = '/Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation'; replace = $true;
           container = 'CACS_AnimTemplateTest_P'; out = $Out },
        @{ template = 'sephiroth'; skeleton = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton';
           package = '/Game/RebirthSkelCompat/AnimTemplateTest/PC0010_00_Sephiroth_Test_Animation'; replace = $true },
        @{ template = 'vincent'; skeleton = '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton';
           package = '/Game/RebirthSkelCompat/AnimTemplateTest/PC0011_00_Vincent_Test_Animation'; replace = $true },
        @{ template = 'monster'; skeleton = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton';
           package = '/Game/RebirthSkelCompat/AnimTemplateTest/Monster_Test_Animation'; replace = $true }
    )
    # the other characters' templates (abp\templates\templates.json), made and compiled for Cloud's skeleton (the project
    # has none of theirs): their graphs, states and rules build in this editor
    foreach ($Key in @('barret', 'tifa', 'aerith', 'redxiii', 'yuffie', 'caitsith', 'moogle', 'zack', 'cid')) {
        $Jobs += @{ template = $Key; skeleton = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton';
                    package = ('/Game/RebirthSkelCompat/AnimTemplateTest/' + $Key + '_Test_Animation'); replace = $true }
    }
    # the AnimBlueprints a test before made: moved out of the project first (to C:\FF7R2UProj\_mod_backups\
    # abp_test_before_<time>\), so each is made new (an editor commandlet cannot delete an asset to replace it)
    $Content = 'C:\FF7R2UProj\Content'
    $Aside = Join-Path 'C:\FF7R2UProj\_mod_backups' ('abp_test_before_{0:yyyyMMdd_HHmmss}' -f (Get-Date))
    foreach ($J in $Jobs) {
        $Rel = $J.package.Substring(6).Replace('/', '\') + '.uasset'
        $File = Join-Path $Content $Rel
        if (Test-Path $File) {
            $To = Join-Path $Aside $Rel
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $To) | Out-Null
            Move-Item -Force -Path $File -Destination $To
            Say ('   the one made before moved aside: Content\' + $Rel + ' -> ' + $To)
        }
    }
    $Text = @{ jobs = $Jobs } | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($Job, $Text, (New-Object System.Text.UTF8Encoding($false)))
    if (Test-Path $Result) { Remove-Item -Force $Result }
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('abp_template_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
    $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(60)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Now = Get-Content -Raw -Path $Result
            if ($Now -match '"done"' -or $Now -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 60 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no result file from the editor (build\abp_template_editor.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    $Ok = $true
    foreach ($Entry in $Json.jobs) {
        $M = $Entry.made
        if ($null -eq $M) { Say ('   ' + $Entry.job.template + ': stopped before it was made'); $Ok = $false; continue }
        Say ('   {0} -> {1}: {2} (compile: {3}; {4} states, {5} conduits, {6} transitions, {7} rule nodes; {8} error(s), {9} warning(s), {10} compiler message(s))' -f
             $Entry.job.template, $Entry.job.package, $(if ($M.ok) { 'MADE' } else { 'NOT MADE' }), $M.compile, $M.states, $M.conduits, $M.transitions,
             $M.rule_nodes, @($M.errors).Count, @($M.warnings).Count, @($M.compiler).Count)
        foreach ($E in @($M.errors) | Select-Object -First 5) { Say ('      ERROR: ' + $E) }
        foreach ($E in @($M.compiler) | Select-Object -First 5) { Say ('      compiler: ' + $E) }
        if (-not $M.ok) { $Ok = $false }
        if ($Entry.job.container) {
            $C = $Entry.cooked
            if ($null -eq $C) { Say '      NOT cooked'; $Ok = $false }
            elseif (-not $C.ok) { Say ('      NOT cooked: ' + (@($C.errors) -join ' / ')); $Ok = $false }
            else { Say ('      cooked: ' + $C.container) }
        }
    }
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR in the editor script: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); $Ok = $false }
    if ($Ok) { exit 0 } else { exit 1 }
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
