# The editor step of run_patch_remake_masters.cmd: opens the End editor with patch_remake_masters.py, which rebuilds a
# few Remake masters in place (Skin, Blood, Hair unless REMAKEPATCH_MASTERS says otherwise), puts the game's static
# switches back on their renderer instances, compiles those and the character instances under them, and closes the editor.
# Exit 0 when it finished ("done": true).
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'status_patch.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$Project = 'C:\FF7R2UProj'
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe'
$Proj = Join-Path $Project 'End.uproject'
$Script = Join-Path $Here 'patch_remake_masters.py'
$Result = Join-Path $Project 'Saved\RemakeMaterials\patch_result.json'
$Log = Join-Path $Build 'editor_patch.log'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('editor_patch_{0}.log' -f $Stamp)) }
    $env:REMAKEPATCH_QUIT = '1'
    $Arguments = "`"$Proj`" -ExecutePythonScript=`"$Script`" -unattended -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(60)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 10
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Json = Get-Content -Raw -Path $Result
            if ($Json -match '"done"') { $DoneAt = Get-Date; Say '   the script finished; waiting for the editor to close' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 240) { Say '   the editor did not close; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 60 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result) -or ((Get-Item $Result).LastWriteTime -lt $Started)) { Say '   no result file (build\editor_patch.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say '   the script stopped before the end (build\editor_patch.log)'; exit 1 }
    Say ('   masters: ' + $Json.masters)
    Say ('   instances: ' + $Json.instances)
    Say ('   notes: ' + @($Json.warnings).Count + ' (Saved\RemakeMaterials\patch_result.json)')
    if (-not $Json.done) { exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
