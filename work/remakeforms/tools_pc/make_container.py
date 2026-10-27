"""REMAKE and REMAKE WINGED, the container step of run_remake_forms.cmd: the moves build_remake_forms.py built (the ones in
Saved/RebirthSkelCompat/RemakeForms/built.json) cooked by the engine's own cook commandlet, then packed with the IoStore
commandlet into _work/Container/RemakeFormsMoves.utoc/.ucas (Sandalphon merges that into the Fully Playable Sephiroth data
containers).

The cook commandlet (without -unversioned, as Package Project cooks) writes tagged properties, which the game reads by
name. The editor's in-process save for the game writes unversioned properties when the project allows them
([Core.System] CanUseUnversionedPropertySerialization, which the editor needs to load the game's cooked copies), and those
are read by position, so a class that differs between the End project and the game would be read wrong.
Prints what it did; exit 0 when the container is there."""
import json, os, shutil, struct, subprocess, sys, time

OUT = r'C:\FF7R2UProj\Saved\RebirthSkelCompat\RemakeForms'
WORK = os.path.join(OUT, '_work')
UE = r'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
PROJECT = r'C:\FF7R2UProj\End.uproject'
NAME = 'RemakeFormsMoves'
MAGIC = struct.pack('<I', 0x9E2A83C1)
PKG_UNVERSIONED_PROPERTIES = 0x2000


def package_flags(path):
    """The package flags of a cooked .uasset (legacy summary: tag, versions, custom versions, header size, folder name)."""
    b = open(path, 'rb').read(4096)
    if b[:4] != MAGIC:
        raise RuntimeError('%s is not a package' % path)
    legacy = struct.unpack_from('<i', b, 4)[0]
    p = 8
    if legacy != -4:
        p += 4                                  # LegacyUE3Version
    p += 8                                      # FileVersionUE4, FileVersionLicenseeUE4
    if legacy <= -2:
        n = struct.unpack_from('<i', b, p)[0]
        p += 4 + 20 * n                         # custom versions (guid + version)
    p += 4                                      # TotalHeaderSize
    n = struct.unpack_from('<i', b, p)[0]
    p += 4 + (n if n >= 0 else -2 * n)          # FolderName
    return struct.unpack_from('<I', b, p)[0]


def main():
    built = json.load(open(os.path.join(OUT, 'built.json')))
    packages = sorted(path.rsplit('.', 1)[0] for path in built)
    if not packages:
        print('FAILED: built.json lists no moves')
        return 1
    # 1. the engine's cook of exactly these packages (no references: the skeleton and the rest are the game's own)
    cook_out = os.path.join(WORK, 'CookOut')
    if os.path.exists(cook_out):
        os.replace(cook_out, os.path.join(WORK, 'CookOut_%s' % time.strftime('%Y%m%d_%H%M%S')))   # (an earlier cook, kept)
    cook_log = os.path.join(WORK, 'cook.log')
    args = [UE, PROJECT, '-run=Cook', '-TargetPlatform=WindowsNoEditor', '-cooksinglepackagenorefs',
            '-map=' + '+'.join(packages), '-OutputDir=' + cook_out, '-ddc=InstalledDerivedDataBackendGraph',
            '-unattended', '-NoLogTimes', '-UTF8Output', '-abslog=' + cook_log]
    started = time.time()
    code = subprocess.call(args, creationflags=0x08000000)
    cooked = {}
    for root, _, files in os.walk(cook_out):
        for name in files:
            if name.endswith('.uasset'):
                path = os.path.join(root, name)
                rel = os.path.relpath(path, cook_out).replace('\\', '/')
                cooked[rel] = path
    wanted = []
    for package in packages:
        tail = 'End/Content/' + package[len('/Game/'):] + '.uasset'
        hit = [rel for rel in cooked if rel == tail or rel.endswith('/' + tail)]
        if len(hit) != 1:
            print('   NOT COOKED: %s (the cook commandlet exited with %d: _work\\cook.log)' % (package, code))
            return 1
        wanted.append((hit[0], cooked[hit[0]]))
    unversioned = [rel for rel, path in wanted if package_flags(path) & PKG_UNVERSIONED_PROPERTIES]
    if unversioned:
        print('   FAILED: the cook wrote unversioned properties (%s)' % ', '.join(unversioned[:3]))
        return 1
    # (the cook's output: <OutputDir>/[<platform>/]End/Content/...)
    prefix = wanted[0][0][:wanted[0][0].find('End/Content/')]
    platform_root = os.path.join(cook_out, prefix.replace('/', os.sep)) if prefix else cook_out
    print('   %d move(s) cooked in %.0f s (tagged properties)' % (len(wanted), time.time() - started))
    # 2. the IoStore container of them
    response = os.path.join(WORK, NAME + '.txt')
    with open(response, 'w', encoding='utf-8') as f:
        for rel, path in wanted:
            under = rel[rel.find('End/Content/') + len('End/Content/'):]
            f.write('"%s" "../../../End/Content/%s"\n' % (path.replace('\\', '/'), under))
    container = os.path.join(WORK, 'Container')
    os.makedirs(container, exist_ok=True)
    os.makedirs(os.path.join(WORK, 'Global'), exist_ok=True)
    utoc = os.path.join(container, NAME + '.utoc')
    for ext in ('.utoc', '.ucas'):
        old = os.path.join(container, NAME + ext)
        if os.path.exists(old):
            os.replace(old, old + '.previous')
    commands = os.path.join(WORK, 'IoStoreCommands.txt')
    with open(commands, 'w', encoding='utf-8') as f:
        f.write('-Output="%s" -ContainerName=%s -ResponseFile="%s"\n' % (utoc.replace('\\', '/'), NAME, response.replace('\\', '/')))
    log = os.path.join(WORK, 'iostore.log')
    args = [UE, PROJECT, '-run=IoStore', '-CreateGlobalContainer=' + os.path.join(WORK, 'Global', 'global.utoc'),
            '-CookedDirectory=' + platform_root, '-Commands=' + commands, '-TargetPlatform=WindowsNoEditor',
            '-ddc=InstalledDerivedDataBackendGraph', '-unattended', '-NoLogTimes', '-UTF8Output', '-abslog=' + log]
    started = time.time()
    code = subprocess.call(args, creationflags=0x08000000)
    ok = os.path.exists(utoc) and os.path.getmtime(utoc) >= started - 1 and os.path.exists(utoc[:-5] + '.ucas')
    if ok:
        print('   container made in %.0f s: %s (%d + %d bytes)%s' % (
            time.time() - started, utoc, os.path.getsize(utoc), os.path.getsize(utoc[:-5] + '.ucas'),
            '' if code == 0 else ' (the commandlet also logged unrelated project warnings, code %d: _work\\iostore.log)' % code))
    else:
        print('   NO CONTAINER: the IoStore commandlet exited with %d (_work\\iostore.log)' % code)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
