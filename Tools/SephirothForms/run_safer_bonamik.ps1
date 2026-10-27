# The editor step of run_safer_bonamik.cmd: runs make_safer_bonamik.py in an editor commandlet (End editor closed).
# Exit 0 when the script made and saved the Bonamik ("ok": true), 1 otherwise. Log: build\bonamik_editor.log
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'bonamik_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'make_safer_bonamik.py'
$Result = 'C:\FF7R2UProj\Saved\SaferBonamik\report.json'
$Log = Join-Path $Build 'bonamik_editor.log'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('bonamik_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
    $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(60)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Text = Get-Content -Raw -Path $Result
            if ($Text -match '"done"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 60 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no report from this run'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if (-not $Json.ok) {
        $Last = if ($Json.PSObject.Properties.Name -contains 'error') { (($Json.error -split "`n") | Where-Object { $_.Trim() } | Select-Object -Last 1) } else { 'stopped before the end' }
        Say ('   ERROR: ' + $Last)
        exit 1
    }
    Say ('   ' + $Json.asset + ' ' + $Json.asset_action + ': ' + $Json.bodies + ' bodies (' + $Json.swinging + ' swinging), ' + $Json.cones + ' cones, ' + $Json.links + ' links, ' + $Json.shapes + ' collision shapes')
    Say ('   mesh: ' + $Json.mesh_action)
    Say ('   saved: ' + ($Json.saved -join ', '))
    foreach ($W in $Json.warnings) { Say ('   note: ' + $W) }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
