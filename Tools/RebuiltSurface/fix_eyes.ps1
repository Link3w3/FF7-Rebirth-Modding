# The editor step of fix_eyes.cmd: puts the game's shared eye textures in /Game/Character/Common/Eye/Texture (the four
# placeholder textures there go to _mod_backups first), then opens the End editor with fix_eye_instances.py, which fills
# the editable eye instances' empty texture slots and closes the editor.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'eyefix_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$Project = 'C:\FF7R2UProj'
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe'
$Proj = Join-Path $Project 'End.uproject'
$Script = Join-Path $Here 'fix_eye_instances.py'
$Result = Join-Path $Project 'Saved\RebirthSkelCompat\EyeFix\result.json'
$Log = Join-Path $Build 'eyefix_editor.log'
$Src = Join-Path $Here '_build\eye_textures'
$Dst = Join-Path $Project 'Content\Character\Common\Eye\Texture'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
try {
    # 1. the textures (the placeholders aside: editor-saved .uasset files without a .uexp)
    New-Item -ItemType Directory -Force -Path $Dst | Out-Null
    $Backup = Join-Path $Project ('_mod_backups\eye_texture_placeholders_' + $Stamp)
    foreach ($F in Get-ChildItem -Path $Dst -Filter '*.uasset') {
        $Base = [IO.Path]::GetFileNameWithoutExtension($F.Name)
        if (-not (Test-Path (Join-Path $Dst ($Base + '.uexp')))) {
            New-Item -ItemType Directory -Force -Path $Backup | Out-Null
            Move-Item -Path $F.FullName -Destination $Backup
            Say ('   placeholder ' + $F.Name + ' moved to ' + $Backup)
        }
    }
    $N = 0
    foreach ($F in Get-ChildItem -Path $Src -File) { Copy-Item -Path $F.FullName -Destination $Dst -Force; $N++ }
    Say ('   ' + $N + ' texture files copied to ' + $Dst)
    # 2. the editor
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('eyefix_editor_{0}.log' -f $Stamp)) }
    $Arguments = "`"$Proj`" -ExecutePythonScript=`"$Script`" -unattended -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(60)
    $DoneAt = $null
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 5
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started) -and ((Get-Content -Raw $Result) -match '"done"')) {
            $DoneAt = Get-Date; Say '   the script finished; waiting for the editor to close'
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 180) { Say '   the editor did not close; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result)) { Say '   no result file (build\eyefix_editor.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    Say ('   checked ' + $Json.checked + ' editable material instances')
    foreach ($F in $Json.fixed) { Say ('   fixed ' + $F.instance + ': ' + ($F.filled -join ', ')) }
    if ($Json.fixed.Count -eq 0) { Say '   no eye instance had empty slots' }
    foreach ($W in $Json.warnings) { Say ('   note: ' + $W) }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
