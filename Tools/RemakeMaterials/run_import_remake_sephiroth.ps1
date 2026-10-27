# The editor step of run_import_remake_mis.cmd: opens the End editor with import_remake_sephiroth.py, which makes FF7 Remake's
# material instances (the 385 renderer instances and Sephiroth's 21) and their textures on the rebuilt Remake masters,
# and closes the editor. Exit 0 when it finished ("done": true).
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'status_seph.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$Project = 'C:\FF7R2UProj'
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe'
$Proj = Join-Path $Project 'End.uproject'
$Script = Join-Path $Here 'import_remake_sephiroth.py'
$Result = Join-Path $Project 'Saved\RemakeMaterials\sephiroth_result.json'
$Log = Join-Path $Build 'editor_seph.log'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('editor_seph_{0}.log' -f $Stamp)) }
    $Arguments = "`"$Proj`" -ExecutePythonScript=`"$Script`" -unattended -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(45)
    $DoneAt = $null
    $LastNote = Get-Date
    while (-not $Process.HasExited) {
        Start-Sleep -Seconds 10
        if (-not $DoneAt -and (Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
            $Json = Get-Content -Raw -Path $Result
            if ($Json -match '"done"') { $DoneAt = Get-Date; Say '   the script finished; waiting for the editor to close' }
        }
        if (((Get-Date) - $LastNote).TotalMinutes -ge 2) {
            $LastNote = Get-Date
            if ((Test-Path $Result) -and ((Get-Item $Result).LastWriteTime -gt $Started)) {
                try { $J = Get-Content -Raw $Result | ConvertFrom-Json; Say ('   progress: ' + ($J.steps -join ', ') + ' (models so far: ' + @($J.meshes.PSObject.Properties).Count + ')') } catch { }
            }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 240) { Say '   the editor did not close; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 45 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result)) { Say '   no result file (build\editor_seph.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say '   the script stopped before the end (build\editor_seph.log)'; exit 1 }
    Say ('   models imported: ' + $Json.meshes_imported)
    foreach ($P in $Json.meshes.PSObject.Properties) {
        if ($P.Value.error) { Say ('   ' + $P.Name + ' FAILED: ' + (($P.Value.error -split "`n") | Select-Object -Last 2) -join ' ') }
        else { Say ('   ' + $P.Name + ': ' + @($P.Value.materials).Count + ' materials on its slots') }
    }
    Say ('   notes: ' + @($Json.warnings).Count + ' (Saved\RemakeMaterials\sephiroth_result.json)')
    if (-not $Json.done) { exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
