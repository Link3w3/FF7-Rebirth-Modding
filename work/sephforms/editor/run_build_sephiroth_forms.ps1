# Builds your playable Sephiroth's winged and flying moves (RebirthSkelCompat move builder, the Move Maker's Build) in
# an editor commandlet: close the End editor first. Status: build\status.txt   Log: build\editor.log
# Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\SephirothForms\ (build_result.json, build_moves.txt, export_json.txt, validate.txt)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
Set-Content -Path $Status -Value ('Sephiroth forms build started {0}' -f (Get-Date))

$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Script = Join-Path $Here 'build_sephiroth_forms.py'
$Result = 'C:\FF7R2UProj\Saved\RebirthSkelCompat\SephirothForms\build_result.json'
$Log = Join-Path $Build 'editor.log'

try {
    if (Get-Process -Name 'UE4Editor' -ErrorAction SilentlyContinue) { Say 'REFUSED: close the End editor first'; Say 'BUILD COMPLETE exit=2'; exit 2 }
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))) }
    $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
    Say 'editor commandlet started (building about 155 moves takes a while)'
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(120)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Text = Get-Content -Raw -Path $Result
            if ($Text -match '"done"' -or $Text -match '"error"') { $DoneAt = Get-Date; Say 'the build script finished; waiting for the editor to exit' }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) {
            Say 'the editor did not exit after the build; stopping it'
            Stop-Process -Id $Process.Id -Force
            break
        }
        if ((Get-Date) -gt $Deadline) {
            Say 'TIMEOUT after 120 minutes; stopping the editor'
            Stop-Process -Id $Process.Id -Force
            break
        }
    }
    $Process.WaitForExit()
    Say "editor exit=$($Process.ExitCode)"
    Say 'BUILD COMPLETE exit=0'
} catch {
    Say ("FAILED: " + $_.Exception.Message)
    Say 'BUILD COMPLETE exit=1'
    exit 1
}
