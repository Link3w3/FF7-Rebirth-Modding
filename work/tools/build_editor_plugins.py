"""Rebuild the End project's own editor plugins with RebirthEngineV5's UnrealBuildTool, one module at a time
(-Module), so End's other modules are untouched:

  RebirthMaterialPreview   C:\\FF7R2UProj\\Plugins\\RebirthMaterialPreview
  RebirthSkelCompatEditor  C:\\FF7R2UProj\\Plugins\\RebirthSkelCompat

For each module the current DLL/PDB/UE4Editor.modules are backed up first and put back if its build fails, so a
failed build leaves the editor exactly as it was. Results: build\\latest.json (and build\\ubt-<module>-<stamp>.log).

RebirthEngineV5's UE4Editor-Engine.dll carries engine additions (RebirthSkeletonCompatibility, ...) that its
UE4Editor-Engine.lib predates, so modules calling them do not link. Before building RebirthMaterialPreview this script
makes RebirthEngineExports.lib (an import library for the DLL's "Rebirth" exports, read from the DLL itself) in that
module's ThirdParty folder; its Build.cs links it when present.

  python build_editor_plugins.py                       both modules (refuses while UE4Editor.exe runs)
  python build_editor_plugins.py RebirthSkelCompatEditor   only the named module(s)
  python build_editor_plugins.py EndDataObject RebirthMaterialPreview   also End's EndDataObject module (built first)

End's own modules (EndDataObject) live in C:\\FF7R2UProj\\Binaries\\Win64, whose UE4Editor.modules lists every End module; that
manifest is left as it is (the BuildId does not change).
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = Path(r'C:\RebirthEngine\RebirthEngineV5\Windows')
PROJECT = Path(r'C:\FF7R2UProj\End.uproject')
PLUGINS = {
    'RebirthMaterialPreview': (PROJECT.parent / 'Plugins' / 'RebirthMaterialPreview', 'RebirthMaterialPreview.uplugin'),
    'RebirthSkelCompatEditor': (PROJECT.parent / 'Plugins' / 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin'),
}
# End's own modules, built only when named; their binaries are the project's.
PROJECT_MODULES = {
    'EndDataObject': PROJECT.parent / 'Source' / 'EndDataObject' / 'EndDataObject.Build.cs',
}


def editor_running() -> bool:
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UE4Editor.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True).stdout
    return 'UE4Editor.exe' in listing


def write_manifest(binaries: Path, module: str) -> str:
    # -Module builds do not write UE4Editor.modules; the editor only loads modules whose BuildId matches the engine.
    engine = json.loads((ENGINE / 'Engine' / 'Binaries' / 'Win64' / 'UE4Editor.modules').read_text(encoding='utf-8-sig'))
    manifest = binaries / 'UE4Editor.modules'
    wanted = {'BuildId': engine['BuildId'], 'Modules': {module: f'UE4Editor-{module}.dll'}}
    try:
        current = json.loads(manifest.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        current = None
    if current != wanted:
        manifest.write_text(json.dumps(wanted, indent=2).replace('\n', '\r\n') + '\r\n', encoding='utf-8')
        return f'wrote {manifest} (BuildId {wanted["BuildId"]})'
    return f'{manifest} already current'


ENGINE_DLL = ENGINE / 'Engine' / 'Binaries' / 'Win64' / 'UE4Editor-Engine.dll'
EXPORTS_LIB = PLUGINS['RebirthMaterialPreview'][0] / 'Source' / 'RebirthMaterialPreview' / 'ThirdParty' / 'RebirthEngineExports.lib'
VS_ROOTS = [Path(r'C:\Program Files\Microsoft Visual Studio\2022') / edition for edition in ('Community', 'Professional', 'Enterprise', 'BuildTools')]
PREFERRED_MSVC = '14.44.35207'


def find_lib_exe() -> Path:
    found = []
    for root in VS_ROOTS:
        tools = root / 'VC' / 'Tools' / 'MSVC'
        if tools.is_dir():
            found += [p for p in tools.iterdir() if (p / 'bin' / 'Hostx64' / 'x64' / 'lib.exe').is_file()]
    if not found:
        raise RuntimeError('lib.exe (Visual Studio 2022 x64 tools) not found')
    preferred = [p for p in found if p.name == PREFERRED_MSVC]
    chosen = preferred[0] if preferred else sorted(found, key=lambda p: [int(x) for x in p.name.split('.') if x.isdigit()])[-1]
    return chosen / 'bin' / 'Hostx64' / 'x64' / 'lib.exe'


def dll_exports(dll: Path) -> list[tuple[str, bool]]:
    """(name, is_code) for every named, non-forwarded export of a PE32+ DLL."""
    data = dll.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    if data[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', data, pe + 24)[0] != 0x20B:
        raise RuntimeError(f'{dll} is not a 64-bit PE image')
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    optional = pe + 24
    first_section = optional + struct.unpack_from('<H', data, pe + 20)[0]
    export_rva, export_size = struct.unpack_from('<II', data, optional + 112)
    table = []
    for i in range(sections):
        at = first_section + 40 * i
        virtual_size, address, raw_size, raw_pointer = struct.unpack_from('<IIII', data, at + 8)
        flags = struct.unpack_from('<I', data, at + 36)[0]
        table.append((address, max(virtual_size, raw_size), raw_pointer, bool(flags & 0x20000000)))

    def section(rva: int):
        for address, size, raw, executable in table:
            if address <= rva < address + size:
                return rva - address + raw, executable
        raise RuntimeError(f'RVA {rva:#x} outside the image')

    def text(rva: int) -> str:
        at = section(rva)[0]
        return data[at:data.index(b'\0', at)].decode('latin-1')

    at = section(export_rva)[0]
    _, _, _, _, _, _, count, names, functions, name_table, ordinals = struct.unpack_from('<IIHHIIIIIII', data, at)
    result = []
    for i in range(names):
        name = text(struct.unpack_from('<I', data, section(name_table)[0] + 4 * i)[0])
        index = struct.unpack_from('<H', data, section(ordinals)[0] + 2 * i)[0]
        if index >= count:
            continue
        rva = struct.unpack_from('<I', data, section(functions)[0] + 4 * index)[0]
        if export_rva <= rva < export_rva + export_size:
            continue  # forwarded
        result.append((name, section(rva)[1]))
    return result


def ensure_engine_exports_lib(out: Path) -> str:
    """Import library for the Engine DLL's "Rebirth" exports, remade when the DLL is newer."""
    if EXPORTS_LIB.exists() and EXPORTS_LIB.stat().st_mtime >= ENGINE_DLL.stat().st_mtime:
        return f'{EXPORTS_LIB} already current'
    wanted = [(name, code) for name, code in dll_exports(ENGINE_DLL) if 'Rebirth' in name]
    if not wanted:
        return f'{ENGINE_DLL.name} exports nothing named Rebirth; no extra import library needed'
    EXPORTS_LIB.parent.mkdir(parents=True, exist_ok=True)
    definition = EXPORTS_LIB.with_suffix('.def')
    lines = [f'LIBRARY "{ENGINE_DLL.name}"', 'EXPORTS'] + [f'    {name}' + ('' if code else ' DATA') for name, code in wanted]
    definition.write_text('\r\n'.join(lines) + '\r\n', encoding='ascii')
    log = out / 'rebirth-engine-exports-lib.log'
    with log.open('wb') as stream:
        code = subprocess.run([str(find_lib_exe()), '/nologo', f'/def:{definition}', '/machine:x64', f'/out:{EXPORTS_LIB}'],
                              stdout=stream, stderr=subprocess.STDOUT, timeout=600).returncode
    if code != 0 or not EXPORTS_LIB.exists():
        raise RuntimeError(f'lib.exe failed ({code}), see {log}')
    return f'made {EXPORTS_LIB} ({len(wanted)} exports of {ENGINE_DLL.name})'


def build(module: str, stamp: str, out: Path) -> dict:
    project_module = module in PROJECT_MODULES
    if project_module:
        binaries = PROJECT.parent / 'Binaries' / 'Win64'
        descriptor_path = PROJECT_MODULES[module]
        files = [f'UE4Editor-{module}.dll', f'UE4Editor-{module}.pdb']
    else:
        plugin, descriptor = PLUGINS[module]
        binaries = plugin / 'Binaries' / 'Win64'
        descriptor_path = plugin / descriptor
        files = [f'UE4Editor-{module}.dll', f'UE4Editor-{module}.pdb', 'UE4Editor.modules']
    result: dict = {'module': module, 'status': 'started'}
    build_bat = ENGINE / 'Engine' / 'Build' / 'BatchFiles' / 'Build.bat'
    for required in (build_bat, PROJECT, descriptor_path):
        if not required.exists():
            result['status'] = f'missing: {required}'
            return result
    backup = HERE / 'backup' / stamp / module
    backup.mkdir(parents=True, exist_ok=True)
    for name in files:
        if (binaries / name).exists():
            shutil.copy2(binaries / name, backup / name)
    result['backup'] = str(backup)
    notes: list = []
    users = dll_users(f'UE4Editor-{module}.dll')
    if users:
        result['dll_loaded_by'] = users
    # A process that still has the old DLL mapped (an editor that has not finished exiting, a cook started by
    # Alpakit) stops the linker from replacing it, but Windows lets a mapped file be renamed. Move the current
    # DLL and PDB aside so the new ones can be written; the renamed files are removed on a later run.
    remove_stale_aside_files(binaries, module, notes)
    aside = []
    for name in files[:2]:
        current = binaries / name
        if current.exists():
            moved = binaries / f'{name}.{stamp}.old'
            try:
                current.rename(moved)
                aside.append((moved, current))
            except OSError as error:
                notes.append(f'could not move {name} aside: {error}')
    log = out / f'ubt-{module}-{stamp}.log'
    command = ['cmd.exe', '/c', str(build_bat), 'EndEditor', 'Win64', 'Development', f'-Project={PROJECT}',
               f'-Module={module}', '-WaitMutex', '-NoHotReloadFromIDE']
    with log.open('wb') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=3600).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    result['log'] = str(log)
    result['exit_code'] = code
    errors = [line for line in text.splitlines() if ': error' in line or 'error C' in line or 'ERROR:' in line
              or 'fatal error' in line]
    if errors:
        result['errors'] = errors[:40]
    dll = binaries / f'UE4Editor-{module}.dll'
    if code == 0 and dll.exists():
        if project_module:
            result['manifest'] = 'project UE4Editor.modules left as it is'
        else:
            result['manifest'] = write_manifest(binaries, module)
        result['dll'] = {'path': str(dll), 'bytes': dll.stat().st_size,
                         'modified': datetime.fromtimestamp(dll.stat().st_mtime, timezone.utc).isoformat()}
        result['status'] = 'OK'
        for moved, _ in aside:
            try:
                moved.unlink()
            except OSError:
                notes.append(f'{moved.name} is still in use; it is removed on a later run')
    else:
        for moved, current in aside:
            try:
                if current.exists():
                    current.unlink()
                moved.rename(current)
            except OSError as error:
                notes.append(f'could not move {moved.name} back: {error}')
        for name in files:
            target = binaries / name
            if (backup / name).exists() and not target.exists():
                try:
                    shutil.copy2(backup / name, target)
                except OSError as error:
                    notes.append(f'could not restore {name} from backup: {error}')
        result['status'] = 'FAILED: previous DLL put back'
    if notes:
        result['notes'] = notes
    result['log_tail'] = text[-2500:]
    return result


def dll_users(dll_name: str) -> list:
    """Image names of running processes that have dll_name loaded (empty when none or when tasklist fails)."""
    try:
        listing = subprocess.run(['tasklist', '/m', dll_name, '/fo', 'csv', '/nh'], capture_output=True, text=True,
                                 timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.split('","')[0].strip('"') + ' pid ' + line.split('","')[1] for line in listing.splitlines()
            if line.startswith('"') and '","' in line]


def remove_stale_aside_files(binaries: Path, module: str, notes: list) -> None:
    for stale in binaries.glob(f'UE4Editor-{module}.*.old'):
        try:
            stale.unlink()
        except OSError:
            notes.append(f'{stale.name} from an earlier run is still in use')


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = HERE / 'build'
    out.mkdir(parents=True, exist_ok=True)
    named = [name for name in sys.argv[1:] if name in PLUGINS or name in PROJECT_MODULES]
    # End's modules first: the plugins link against them.
    wanted = sorted(named, key=lambda name: 0 if name in PROJECT_MODULES else 1) or list(PLUGINS)
    summary: dict = {'stamp': stamp, 'status': 'started', 'modules': []}
    try:
        if editor_running():
            summary['status'] = 'refused: UE4Editor.exe is running, close the End editor first'
            return 2
        if 'RebirthMaterialPreview' in wanted:
            summary['engine_exports'] = ensure_engine_exports_lib(out)
        for module in wanted:
            summary['modules'].append(build(module, stamp, out))
        failed = [m['module'] for m in summary['modules'] if m['status'] != 'OK']
        summary['status'] = 'OK' if not failed else 'FAILED: ' + ', '.join(failed)
        return 0 if not failed else 1
    except Exception as error:  # report everything to the result file
        summary['status'] = f'FAILED: {type(error).__name__}: {error}'
        return 1
    finally:
        (out / 'latest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps({k: v for k, v in summary.items() if k != 'modules'}, indent=2))
        for module in summary['modules']:
            print(json.dumps({k: v for k, v in module.items() if k != 'log_tail'}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
