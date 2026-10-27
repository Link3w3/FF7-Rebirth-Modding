# The editor step of run_dirge_motions.cmd: runs cook_dirge_motions.py in an editor commandlet (End editor closed).
# The script makes one motion at a time and says in motions_progress.json which one it is making: when the editor stops in
# the middle of one, it is run again (up to 12 times) and leaves that motion out. Exit 0 when the script finished, 1 otherwise.
# Log: build\dirge_motions_editor.log (each earlier run's kept by time).
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'dirge_motions_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'cook_dirge_motions.py'
$Result = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\VincentDirge\motions_result.json'
$Progress = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\VincentDirge\motions_progress.json'
$Log = Join-Path $Build 'dirge_motions_editor.log'
$MostRuns = 12
try {
    for ($Run = 1; $Run -le $MostRuns; $Run++) {
        if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('dirge_motions_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
        $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
        $Started = Get-Date
        if ($Run -gt 1) { Say "   editor run $Run" }
        $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
        $null = $Process.Handle
        $Deadline = (Get-Date).AddMinutes(150)
        $DoneAt = $null
        while (-not $Process.HasExited) {
            Start-Sleep -Seconds 5
            if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
                $Text = Get-Content -Raw -Path $Result
                if ($Text -match '"done"' -or $Text -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
            }
            if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
            if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 150 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
        }
        $Process.WaitForExit()
        Say "   editor exit=$($Process.ExitCode)"
        if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no result file from this run'; exit 1 }
        $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
        if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
        if (-not ($Json.PSObject.Properties.Name -contains 'done')) {
            $Current = $null
            if ((Test-Path $Progress) -and (Get-Item $Progress).LastWriteTime -gt $Started) {
                $State = Get-Content -Raw -Path $Progress | ConvertFrom-Json
                $Current = $State.current
            }
            if ($Current) { Say "   the editor stopped while it made $Current`: it is left out, the others go on"; continue }
            Say ('   the script stopped before the end (after: ' + ($Json.steps | Select-Object -Last 1) + ')')
            exit 1
        }
        foreach ($Key in @('old_labels', 'model_label', 'motions_Vincent', 'motions_Chaos')) {
            if ($Json.PSObject.Properties.Name -contains $Key) { Say ('   ' + $Key + ': ' + (($Json.$Key | Out-String).Trim() -replace "`r?`n", '; ')) }
        }
        exit 0
    }
    Say "   the editor stopped $MostRuns times: see build\dirge_motions_editor*.log"
    exit 1
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
