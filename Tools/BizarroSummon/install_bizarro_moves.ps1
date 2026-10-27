# The work of install_bizarro_moves.cmd: puts Bizarro Sephiroth's own moves for his summon into the game (game closed):
#   FullyPlayableSephirothDataAssets_P (.ucas, .utoc) - the summon's abilities play his attacks, with his damage,
#   BizarroSummon.json - his own battle sets for the summon (Create a Character System).
# Every file is checked (MD5) before and after it is copied. If any of them cannot go in, the previous container comes
# back from the backup, so the game never gets a .ucas and .utoc (or abilities and animation sets) that do not belong
# together. Exit 0 when everything is in. Status: build\install_moves_status.txt
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Build = Join-Path $Here 'build'
New-Item -ItemType Directory -Force -Path $Build | Out-Null
$Status = Join-Path $Build 'install_moves_status.txt'
function Say([string]$Text) { Add-Content -Path $Status -Value ('{0:HH:mm:ss} {1}' -f (Get-Date), $Text); Write-Host $Text }
function Md5([string]$Path) { (Get-FileHash -Algorithm MD5 -LiteralPath $Path).Hash.ToUpperInvariant() }

$Staging = 'C:\FF7R2UProj\Tools\SephirothForms-backups\staging-bizmoves1015a'
$Backup = 'C:\FF7R2UProj\Tools\SephirothForms-backups\backup-20261015d'
$Game = 'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End'
$Mods = Join-Path $Game 'Content\Paks\~mods'
$Compat = Join-Path $Game 'Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat'
$Files = @(
    @{ Name = 'FullyPlayableSephirothDataAssets_P.ucas'; To = $Mods; Md5 = '61D01B135408E58EA00E0B328181CBEC'; Old = (Join-Path $Backup 'mods-data') },
    @{ Name = 'FullyPlayableSephirothDataAssets_P.utoc'; To = $Mods; Md5 = '0CB86D147B08B43B200CB74C5C4FFFD8'; Old = (Join-Path $Backup 'mods-data') },
    @{ Name = 'BizarroSummon.json'; To = $Compat; Md5 = '1415D96B5E1D5B75FA4BAEB9290C8D00'; Old = (Join-Path $Backup 'compat') }
)

# The previous container back in place (each of its files that is not the previous one already).
function PutBack {
    foreach ($Name in 'FullyPlayableSephirothDataAssets_P.ucas', 'FullyPlayableSephirothDataAssets_P.utoc') {
        $Old = Join-Path (Join-Path $Backup 'mods-data') $Name
        $Now = Join-Path $Mods $Name
        try {
            if ((Test-Path -LiteralPath $Now) -and ((Md5 $Now) -eq (Md5 $Old))) { continue }
            Copy-Item -Force -LiteralPath $Old -Destination $Now
            Say "   put back the previous $Name"
        } catch {
            Say "   COULD NOT PUT BACK $Name ($($_.Exception.Message)): copy it from $Backup\mods-data by hand before playing"
        }
    }
}

try {
    if (Get-Process -Name 'ff7rebirth_', 'ff7rebirth' -ErrorAction SilentlyContinue) {
        Say 'REFUSED: the game is running. Close FINAL FANTASY VII REBIRTH, then run this again.'
        exit 1
    }
    foreach ($F in $Files) {
        $From = Join-Path $Staging $F.Name
        if (-not (Test-Path -LiteralPath $From)) { Say "FAILED: $From is missing"; exit 1 }
        if ((Md5 $From) -ne $F.Md5) { Say "FAILED: $From is not the file it should be (MD5)"; exit 1 }
        if (-not (Test-Path -LiteralPath (Join-Path $F.Old $F.Name))) { Say "FAILED: the backup of $($F.Name) is missing in $($F.Old)"; exit 1 }
    }
    Say 'the new files are the right ones; the previous ones are backed up in backup-20261015d'
    foreach ($F in $Files) {
        $To = Join-Path $F.To $F.Name
        try {
            Copy-Item -Force -LiteralPath (Join-Path $Staging $F.Name) -Destination $To
        } catch {
            Say "FAILED to copy $($F.Name): $($_.Exception.Message)"
            PutBack
            exit 1
        }
        if ((Md5 $To) -ne $F.Md5) {
            Say "FAILED: $To did not come out right (MD5)"
            PutBack
            exit 1
        }
        Say "   installed $($F.Name) (MD5 checked)"
    }
    Say 'DONE: the Bizarro Sephiroth summon fights with his own moves now. Start the game and call the summon.'
    exit 0
} catch {
    Say ('FAILED: ' + $_.Exception.Message)
    PutBack
    exit 1
}
