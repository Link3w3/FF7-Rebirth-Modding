# Self-test of data asset and blueprint editing: two editor commandlet runs (close the End editor first).
# Status: build\asset_test_status.txt   Logs: build\asset_step1.log, build\asset_step2.log
# Results: C:\FF7R2UProj\Saved\RebirthDataObjectTests\asset_step1.json, asset_step2.json
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'asset_test_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text) }
Set-Content -Path $Status -Value ('Data asset test started {0}' -f (Get-Date))

$UE = 'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$Proj = 'C:\FF7R2UProj\End.uproject'
$Content = 'C:\FF7R2UProj\Content'
$Tests = Join-Path $Content 'RebirthDataObjectTests'
$Out = 'C:\FF7R2UProj\Saved\RebirthDataObjectTests'

try {
    if (Get-Process -Name 'UE4Editor' -ErrorAction SilentlyContinue) { Say 'REFUSED: close the End editor first'; Say 'TEST COMPLETE exit=2'; exit 2 }

    # Earlier data asset and blueprint test assets are moved aside (not deleted).
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    foreach ($Name in @('asset_step1.json', 'asset_step2.json')) {
        $File = Join-Path $Out $Name
        if (Test-Path $File) {
            $Old = Join-Path $Out 'previous'
            New-Item -ItemType Directory -Force -Path $Old | Out-Null
            Move-Item -Force -Path $File -Destination (Join-Path $Old $Name)
        }
    }
    foreach ($Sub in @('DataAssets', 'BP')) {
        $Dir = Join-Path $Tests $Sub
        if (Test-Path $Dir) {
            $Aside = Join-Path $Out ('previous_{0}_{1:yyyyMMdd_HHmmss}' -f $Sub, (Get-Date))
            Move-Item -Path $Dir -Destination $Aside
            Say "Earlier test assets moved to $Aside"
        }
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $Tests 'DataAssets') | Out-Null
    $Source = Join-Path $Content 'DataAsset\Game\CharaSpec\CharaSpec_PC0000_00_Cloud_Standard'
    if (-not (Test-Path "$Source.uexp")) { Say 'FAILED: the cooked CharaSpec_PC0000_00_Cloud_Standard was not found'; Say 'TEST COMPLETE exit=3'; exit 3 }
    Copy-Item -Force "$Source.uasset" (Join-Path $Tests 'DataAssets\CharaSpec_PC0000_00_Cloud_Standard.uasset')
    Copy-Item -Force "$Source.uexp" (Join-Path $Tests 'DataAssets\CharaSpec_PC0000_00_Cloud_Standard.uexp')
    Say "Cooked data asset copied from $Source"

    function Run-Step([string]$Name, [string]$Script, [string]$Json, [int]$Minutes) {
        $Log = Join-Path $Build "asset_$Name.log"
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

    Run-Step 'step1' (Join-Path $Here 'asset_test_step1.py') (Join-Path $Out 'asset_step1.json') 30
    Run-Step 'step2' (Join-Path $Here 'asset_test_step2.py') (Join-Path $Out 'asset_step2.json') 20
    Say 'TEST COMPLETE exit=0'
} catch {
    Say ("FAILED: " + $_.Exception.Message)
    Say 'TEST COMPLETE exit=1'
    exit 1
}
