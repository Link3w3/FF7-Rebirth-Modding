# The editor step of run_build_remake_materials.cmd: opens the End editor with build_remake_materials.py, which builds
# FF7 Remake's default textures, material functions and EndMaterial masters at /Game/GameContents/Renderer, compiles
# them (and, with -Permutations, every one of the game's static permutations of them) and closes the editor.
# Exit 0 when it finished ("done": true).
param([switch]$Permutations)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
$Project = 'C:\FF7R2UProj'
$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe'
$Proj = Join-Path $Project 'End.uproject'
$Script = Join-Path $Here 'build_remake_materials.py'
$Result = Join-Path $Project 'Saved\RemakeMaterials\build_result.json'
$Log = Join-Path $Build 'editor.log'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
try {
    if (Test-Path $Log) { Move-Item -Force -Path $Log -Destination (Join-Path $Build ('editor_{0}.log' -f $Stamp)) }
    $env:REMAKEMATERIALS_PERMUTATIONS = $(if ($Permutations) { '1' } else { '0' })
    $Arguments = "`"$Proj`" -ExecutePythonScript=`"$Script`" -unattended -nosplash -nosound -abslog=`"$Log`""
    $Started = Get-Date
    $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru
    $null = $Process.Handle
    $Deadline = (Get-Date).AddMinutes(180)
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
                try { $J = Get-Content -Raw $Result | ConvertFrom-Json; Say ('   progress: ' + ($J.steps -join ', ') + ' (masters so far: ' + @($J.materials.PSObject.Properties).Count + ')') } catch { }
            }
        }
        if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 240) { Say '   the editor did not close; stopping it'; Stop-Process -Id $Process.Id -Force; break }
        if ((Get-Date) -gt $Deadline) { Say '   TIMEOUT after 180 minutes; stopping the editor'; Stop-Process -Id $Process.Id -Force; break }
    }
    $Process.WaitForExit()
    Say "   editor exit=$($Process.ExitCode)"
    if (-not (Test-Path $Result)) { Say '   no result file (build\editor.log)'; exit 1 }
    $Json = Get-Content -Raw -Path $Result | ConvertFrom-Json
    if ($Json.PSObject.Properties.Name -contains 'error') { Say ('   ERROR: ' + (($Json.error -split "`n") | Select-Object -Last 3) -join ' '); exit 1 }
    if (-not ($Json.PSObject.Properties.Name -contains 'done')) { Say '   the script stopped before the end (build\editor.log)'; exit 1 }
    Say ('   textures: ' + $Json.textures)
    Say ('   functions built: ' + $Json.functions_built)
    Say ('   masters built: ' + $Json.masters_built)
    foreach ($P in $Json.materials.PSObject.Properties) {
        $C = $P.Value.compile
        if ($C -and -not $C.ok) { Say ('   ' + $P.Name + ' compile errors: ' + (($C.errors | Select-Object -First 3) -join ' | ')) }
        if ($P.Value.built -eq 'FAILED') { Say ('   ' + $P.Name + ' FAILED') }
    }
    if ($Json.PSObject.Properties.Name -contains 'permutations') { Say ('   permutations: ' + $Json.permutations) }
    Say ('   notes: ' + @($Json.warnings).Count + ' (Saved\RemakeMaterials\build_result.json)')
    if (-not $Json.done) { exit 1 }
    exit 0
} catch {
    Say ('   FAILED: ' + $_.Exception.Message)
    exit 1
}
