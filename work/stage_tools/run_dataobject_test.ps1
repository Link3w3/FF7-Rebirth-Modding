# Self-test of the Rebirth data object tools: two editor commandlet runs (close the End editor first).
# Status: build\dataobject_test_status.txt   Logs: build\dataobject_step1.log, build\dataobject_step2.log
# Results: C:\FF7R2UProj\Saved\RebirthDataObjectTests\step1.json, step2.json, all_dataobjects.json
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'dataobject_test_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
Set-Content -Path $Status -Value ('Data object test started {0}' -f (Get-Date))

$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Content = 'C:\FF7R2UProj\Content'
$Tests = Join-Path $Content 'RebirthDataObjectTests'
$Out = 'C:\FF7R2UProj\Saved\RebirthDataObjectTests'

try {
    if (Get-Process -Name 'UE4Editor' -ErrorAction SilentlyContinue) { Say 'REFUSED: close the End editor first'; Say 'TEST COMPLETE exit=2'; exit 2 }

    # Fresh results; the test assets of an earlier run are moved aside (not deleted).
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    Get-ChildItem -Path $Out -File -ErrorAction SilentlyContinue | ForEach-Object {
        $Old = Join-Path $Out 'previous'
        New-Item -ItemType Directory -Force -Path $Old | Out-Null
        Move-Item -Force -Path $_.FullName -Destination (Join-Path $Old $_.Name)
    }
    if (Test-Path $Tests) {
        $Aside = Join-Path $Out ('previous_assets_{0:yyyyMMdd_HHmmss}' -f (Get-Date))
        Move-Item -Path $Tests -Destination $Aside
        Say "Earlier test assets moved to $Aside"
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $Tests 'Cooked') | Out-Null

    # The cooked CharaSpec: the project's own file while it is still cooked, else the newest backup made by Make Editable.
    $Source = $null
    if (Test-Path (Join-Path $Content 'DataObject\Resident\CharaSpec.uexp')) {
        $Source = Join-Path $Content 'DataObject\Resident\CharaSpec'
    } else {
        $Backups = 'C:\FF7R2UProj\Saved\RebirthDataObjectBackups'
        if (Test-Path $Backups) {
            $Found = Get-ChildItem -Path $Backups -Directory | Sort-Object Name -Descending | Where-Object { Test-Path (Join-Path $_.FullName 'Game\DataObject\Resident\CharaSpec.uexp') } | Select-Object -First 1
            if ($Found) { $Source = Join-Path $Found.FullName 'Game\DataObject\Resident\CharaSpec' }
        }
    }
    if (-not $Source) { Say 'FAILED: no cooked CharaSpec found (project or backups)'; Say 'TEST COMPLETE exit=3'; exit 3 }
    Copy-Item -Force "$Source.uasset" (Join-Path $Tests 'Cooked\CharaSpec.uasset')
    Copy-Item -Force "$Source.uexp" (Join-Path $Tests 'Cooked\CharaSpec.uexp')
    Set-Content -Path (Join-Path $Out 'cooked_source.txt') -Value $Source
    Say "Cooked CharaSpec copied from $Source"

    function Run-Step([string]$Name, [string]$Script, [string]$Json, [int]$Minutes) {
        $Log = Join-Path $Build "dataobject_$Name.log"
        $Arguments = "`"$Proj`" -run=pythonscript -script=`"$Script`" -unattended -nopause -nosplash -nosound -abslog=`"$Log`""
        Say "$Name started"
        $Process = Start-Process -FilePath $UE -ArgumentList $Arguments -PassThru -WindowStyle Hidden
        $null = $Process.Handle
        $Deadline = (Get-Date).AddMinutes($Minutes)
        $DoneAt = $null
        while (-not $Process.HasExited) {
            Start-Sleep -Seconds 2
            if (-not $DoneAt -and (Test-Path $Json)) { $DoneAt = Get-Date }
            if ($DoneAt -and ((Get-Date) - $DoneAt).TotalSeconds -gt 120) {
                Say "$Name finished its work but did not exit; stopping it"
                Stop-Process -Id $Process.Id -Force
                break
            }
            if ((Get-Date) -gt $Deadline) {
                Say "$Name TIMEOUT after $Minutes minutes; stopping it"
                Stop-Process -Id $Process.Id -Force
                break
            }
        }
        $Process.WaitForExit()
        Say "$Name exit=$($Process.ExitCode)"
    }

    Run-Step 'step1' (Join-Path $Here 'dataobject_test_step1.py') (Join-Path $Out 'step1.json') 40
    Run-Step 'step2' (Join-Path $Here 'dataobject_test_step2.py') (Join-Path $Out 'step2.json') 20
    Say 'TEST COMPLETE exit=0'
} catch {
    Say ("FAILED: " + $_.Exception.Message)
    Say 'TEST COMPLETE exit=1'
    exit 1
}
