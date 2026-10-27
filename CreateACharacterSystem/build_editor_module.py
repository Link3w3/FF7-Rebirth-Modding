"""Build one editor module of the End project with the RebirthEngineV5 UnrealBuildTool, only that module (-Module):
ENDEditor (End's own editor module: the AnimGraph nodes of the game's End anim nodes, editor 1.19) or
RebirthSkelCompatEditor (the Create a Character System editor plugin). Its binaries' module list (UE4Editor.modules)
is kept whole: the editor loads a module only when that list names it with the engine's BuildId.

  build_editor_module.py <module> <log file>      (refuses while UE4Editor.exe runs: Live Coding blocks module builds)
Prints a JSON result last; exit code UnrealBuildTool's (2: refused or missing files)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(r'C:\RebirthEngine\RebirthEngineV5\Windows')
PROJECT = Path(r'C:\FF7R2UProj\End.uproject')
MODULES = {
    'ENDEditor': PROJECT.parent / 'Binaries' / 'Win64',
    'RebirthSkelCompatEditor': PROJECT.parent / 'Plugins' / 'RebirthSkelCompat' / 'Binaries' / 'Win64',
}


def editor_running() -> bool:
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UE4Editor.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
    return 'UE4Editor.exe' in listing


def read_manifest(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def keep_manifest(binaries: Path, module: str, before) -> str:
    """The module list after the build: every module it named before (End's other modules), this one, the engine's BuildId."""
    engine = json.loads((ENGINE / 'Engine' / 'Binaries' / 'Win64' / 'UE4Editor.modules').read_text(encoding='utf-8-sig'))
    manifest = binaries / 'UE4Editor.modules'
    now = read_manifest(manifest)
    modules = {}
    for m in (before, now):
        if m and isinstance(m.get('Modules'), dict):
            modules.update(m['Modules'])
    modules[module] = f'UE4Editor-{module}.dll'
    wanted = {'BuildId': engine['BuildId'], 'Modules': dict(sorted(modules.items(), key=lambda kv: kv[0].lower()))}
    if now != wanted:
        manifest.write_text(json.dumps(wanted, indent='\t').replace('\n', '\r\n') + '\r\n', encoding='utf-8')
        return f'wrote {manifest} ({len(modules)} modules, BuildId {wanted["BuildId"]})'
    return f'{manifest} already current'


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in MODULES:
        print('usage: build_editor_module.py <%s> <log file>' % '|'.join(MODULES))
        return 2
    module, log = sys.argv[1], Path(sys.argv[2])
    if editor_running():
        print('UE4Editor.exe is running. Close the End editor first.')
        return 2
    build_bat = ENGINE / 'Engine' / 'Build' / 'BatchFiles' / 'Build.bat'
    for required in (build_bat, PROJECT):
        if not required.exists():
            print(f'Missing: {required}')
            return 2
    binaries = MODULES[module]
    before = read_manifest(binaries / 'UE4Editor.modules')
    binary = binaries / f'UE4Editor-{module}.dll'
    old_time = binary.stat().st_mtime if binary.exists() else None
    log.parent.mkdir(parents=True, exist_ok=True)
    command = ['cmd.exe', '/c', str(build_bat), 'EndEditor', 'Win64', 'Development', f'-Project={PROJECT}', f'-Module={module}',
               '-WaitMutex', '-NoHotReloadFromIDE']
    with log.open('wb') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=3600).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    result = {'module': module, 'exit_code': code, 'log': str(log), 'binary': str(binary) if binary.exists() else None,
              'rebuilt': bool(binary.exists() and (old_time is None or binary.stat().st_mtime > old_time))}
    if code == 0 and binary.exists():
        result['manifest'] = keep_manifest(binaries, module, before)
    errors = [line for line in text.splitlines() if ': error' in line or 'error C' in line or 'error LNK' in line or 'ERROR:' in line]
    if errors:
        result['errors'] = errors[:40]
    print(text[-2500:])
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
