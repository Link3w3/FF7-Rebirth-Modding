# The editor step of run_death_penalty.cmd: runs label_death_penalty.py in an editor commandlet (End editor closed).
# Exit 0 when the script finished ("done"), 1 otherwise. Log: build\death_penalty_editor.log
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'death_penalty_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'label_death_penalty.py'
$Result = 'C:\FF7R2UProj\Saved\ChaosDeathPenalty\label_result.json'
$Log = Join-Path $Build 'death_penalty_editor.log'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('death_penalty_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
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
            if ($Text -match '"done"' -or $Text -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 60 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no result file from the editor'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    foreach ($Key in @('chunk', 'label')) { if ($Json.PSObject.Properties.Name -contains $Key) { Say ('   ' + $Json.$Key) } }
    if ($Json.PSObject.Properties.Name -contains 'materials') { Say ('   materials: ' + ($Json.materials -join '; ')) }
    if ($Json.PSObject.Properties.Name -contains 'mesh') { Say ('   mesh: ' + (($Json.mesh | ConvertTo-Json -Compress -Depth 4))) }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say ('   the script stopped before the end (after: ' + ($Json.steps | Select-Object -Last 1) + ')'); exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
