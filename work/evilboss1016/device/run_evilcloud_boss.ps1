# The editor step of run_evilcloud_boss.cmd: runs build_evilcloud_boss.py in an editor commandlet (End editor closed).
# The script builds one move at a time and says in progress.json which one it is building: when the editor stops in the
# middle of one, it is run again (up to 12 times), and the script leaves that move out and keeps the moves built already.
# Exit 0 when the script finished ("done": true), 1 otherwise. Log: build\boss_editor.log (each earlier run's kept by time)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'boss_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'build_evilcloud_boss.py'
$Result = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\EvilCloudBoss\build_result.json'
$Progress = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\EvilCloudBoss\progress.json'
$Log = Join-Path $Build 'boss_editor.log'
$MostRuns = 12
try {
    for ($Run = 1; $Run -le $MostRuns; $Run++) {
        if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('boss_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
        $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
        $Started = Get-Date
        if ($Run -gt 1) { Say "   editor run $Run" }
        $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
        $null = $Process.Handle
        $Deadline = (Get-Date).AddMinutes(240)
        $DoneAt = $null
        while (-not $Process.HasExited) {
            Start-Sleep -Seconds 5
            if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
                $Text = Get-Content -Raw -Path $Result
                if ($Text -match '"done"' -or $Text -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
            }
            if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
            if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 240 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
        }
        $Process.WaitForExit()
        Say "   editor exit=$($Process.ExitCode)"
        if (-not (Test-Path $Result) -or (Get-Item $Result).LastWriteTime -lt $Started) { Say '   no result file from this run'; exit 1 }
        $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
        if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 2) -join ' '); exit 1 }
        if (-not ($Json.PSObject.Properties.Name -contains 'done')) {
            # stopped in the middle of a move: run again without it
            $Current = $null
            if ((Test-Path $Progress) -and (Get-Item $Progress).LastWriteTime -gt $Started) {
                $State = Get-Content -Raw -Path $Progress | ConvertFrom-Json
                $Current = $State.current
            }
            if ($Current) {
                Say ("   the editor stopped while it built $Current ($($State.done.PSObject.Properties.Name.Count) built so far): it is left out, the others go on")
                continue
            }
            Say ('   the script stopped before the end (after: ' + ($Json.steps | Select-Object -Last 1) + ')')
            exit 1
        }
        Say ('   ' + $Json.run)
        Say ('   sources: ' + $Json.sources)
        Say ('   ' + $Json.row)
        Say ('   build: ' + $Json.build)
        Say ('   ' + $Json.effect_parameters)
        if ($Json.PSObject.Properties.Name -contains 'compression') { Say ('   saved as: ' + (($Json.compression.PSObject.Properties | ForEach-Object { '{0} x{1}' -f $_.Name, $_.Value }) -join ', ')) }
        if ($Json.failed.Count -gt 0) { Say ('   not built (the boss''s own stays for these): ' + ($Json.failed -join ', ')) }
        Say ('   checked: ' + $Json.checked)
        if (-not $Json.done) { exit 1 }
        exit 0
    }
    Say "   the editor stopped $MostRuns times: see build\boss_editor*.log"
    exit 1
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
