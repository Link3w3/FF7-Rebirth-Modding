# The editor step of run_bizarro_survey.cmd: runs survey_bizarro.py in an editor commandlet (End editor closed).
# Exit 0 when the script finished ("done": true), 1 otherwise. Log: build\survey_editor.log
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'survey_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'survey_bizarro.py'
$Result = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\BizarroSummon\survey_result.json'
$Log = Join-Path $Build 'survey_editor.log'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('survey_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
    $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(90)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Text = Get-Content -Raw -Path $Result
            if ($Text -match '"done"' -or $Text -match '"error"') { $DoneAt = Get-Date; Say '   the editor script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not exit; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 90 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result)) { Say '   no result file'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 2) -join ' '); exit 1 }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say '   the script stopped before the end'; exit 1 }
    Say ('   described: ' + $Json.described)
    if (-not $Json.done) { exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
