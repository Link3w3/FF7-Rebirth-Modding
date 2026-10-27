# The editor step of run_build_rebuilt_surface.cmd:
#   1. moves the game's cooked RM_Surface (Content\Renderer\Material\RM_Surface.uasset/.uexp) into _mod_backups,
#   2. opens the End editor with build_rm_surface.py, which builds the rebuilt RM_Surface in its place, compiles the game's
#      104 permutations of it and closes the editor.
# If the new RM_Surface was not saved, the cooked one is put back. Exit 0 when it finished ("done": true).
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$Project = 'C:\FF7R2UProj'
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe'
$Proj = Join-Path $Project 'End.uproject'
$Script = Join-Path $Here 'build_rm_surface.py'
$Result = Join-Path $Project 'Saved\RebirthSkelCompat\RebuiltSurface\build_result.json'
$Log = Join-Path $Build 'editor.log'
$MatDir = Join-Path $Project 'Content\Renderer\Material'
$Asset = Join-Path $MatDir 'RM_Surface.uasset'
$Exp = Join-Path $MatDir 'RM_Surface.uexp'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Moved = $null
try {
    # 1. the cooked RM_Surface aside (an editor-saved RM_Surface has no .uexp)
    if (Test-Path $Exp) {
        $Moved = Join-Path $Project ('_mod_backups\RM_Surface_cooked_' + $Stamp)
        New-Item -ItemType Directory -Force -Path $Moved | Out-Null
        Move-Item -Path $Asset -Destination $Moved
        Move-Item -Path $Exp -Destination $Moved
        Set-Content -Path (Join-Path $Build 'cooked_backup.txt') -Value $Moved
        Say ('   the game''s cooked RM_Surface moved to ' + $Moved)
    } elseif (Test-Path $Asset) {
        Say '   RM_Surface is already the rebuilt one: building it again in place'
    }
    # 2. the editor
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('editor_{0}.log' -f $Stamp)) }
    $Arguments = "`"$Proj`" -ExecutePythonScript=`"$Script`" -unattended -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(150)
    $DoneAt = $null
    $LastNote = Get-Date
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 10
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Json = Get-Content -Raw -Path $Result
            if ($Json -match '"done"') { $DoneAt = Get-Date; Say '   the script finished; waiting for the editor to close' }
        }
        if (((Get-Date) - $LastNote).TotalMinutes -ge 5) {
            $LastNote = Get-Date
            $Perm = Join-Path $Project 'Saved\RebirthSkelCompat\RebuiltSurface\permutations.json'
            if ((Test-Path $Perm) -and ((Get-Item $Perm).LastWriteTime -gt $Started)) { try { Say ('   permutations checked so far: ' + ((Get-Content -Raw $Perm | ConvertFrom-Json).Count)) } catch { } }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 240) { Say '   the editor did not close; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 150 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    $Saved = (Test-Path $Asset) -and -not (Test-Path $Exp)
    if (-not $Saved -and $Moved) {
        Move-Item -Path (Join-Path $Moved 'RM_Surface.uasset') -Destination $MatDir
        Move-Item -Path (Join-Path $Moved 'RM_Surface.uexp') -Destination $MatDir
        Say '   the rebuilt RM_Surface was not saved: the game''s cooked RM_Surface is back in place'
    }
    if (-not (Test-Path $Result)) { Say '   no result file (build\editor.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say '   the script stopped before the end (build\editor.log)'; exit 1 }
    Say ('   saved: ' + $Json.saved)
    Say ('   base compile: ' + ($Json.base_compile | ConvertTo-Json -Compress -Depth 4))
    Say ('   permutations: ' + $Json.permutations)
    foreach ($W in $Json.warnings) { Say ('   note: ' + $W) }
    if (-not $Json.done) { exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    if ($Moved -and -not (Test-Path $Asset)) {
        Move-Item -Path (Join-Path $Moved 'RM_Surface.uasset') -Destination $MatDir
        Move-Item -Path (Join-Path $Moved 'RM_Surface.uexp') -Destination $MatDir
        Say '   the game''s cooked RM_Surface is back in place'
    }
    exit 1
}
