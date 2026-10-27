"""Build the KawaiiPhysics plugin (C:\\FF7R2UProj\\Plugins\\KawaiiPhysics: its modules KawaiiPhysics and KawaiiPhysicsEd)
with the RebirthEngineV5 UnrealBuildTool. Only those modules are compiled (-Module), so End's own modules are untouched.

  python build_kawaii_plugin.py           build (refuses while UE4Editor.exe runs: Live Coding blocks module builds)
  python build_kawaii_plugin.py --force   build even if an editor is running
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = Path(r'C:\RebirthEngine\RebirthEngineV5\Windows')
PROJECT = Path(r'C:\FF7R2UProj\End.uproject')
PLUGIN = PROJECT.parent / 'Plugins' / 'KawaiiPhysics'
MODULES = ['KawaiiPhysics', 'KawaiiPhysicsEd']


def editor_running() -> bool:
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UE4Editor.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True).stdout
    return 'UE4Editor.exe' in listing


def write_manifest(binaries: Path) -> str:
    # -Module builds do not write UE4Editor.modules. The editor only loads modules whose manifest
    # BuildId matches the engine's, so mirror the engine's BuildId (same as End's own modules).
    engine_manifest = json.loads((ENGINE / 'Engine' / 'Binaries' / 'Win64' / 'UE4Editor.modules').read_text(encoding='utf-8-sig'))
    manifest = binaries / 'UE4Editor.modules'
    wanted = {'BuildId': engine_manifest['BuildId'], 'Modules': {m: f'UE4Editor-{m}.dll' for m in MODULES}}
    try:
        current = json.loads(manifest.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        current = None
    if current != wanted:
        manifest.write_text(json.dumps(wanted, indent=2).replace('\n', '\r\n') + '\r\n', encoding='utf-8')
        return f'wrote {manifest} (BuildId {wanted["BuildId"]})'
    return f'{manifest} already current'


def main() -> int:
    if editor_running() and '--force' not in sys.argv:
        print('UE4Editor.exe is running. Close the End editor first (or pass --force).')
        return 2
    build_bat = ENGINE / 'Engine' / 'Build' / 'BatchFiles' / 'Build.bat'
    for required in (build_bat, PROJECT, PLUGIN / 'KawaiiPhysics.uplugin'):
        if not required.exists():
            print(f'Missing: {required}')
            return 2
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    logs = HERE / 'build' / 'kawaii_plugin'
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f'ubt-{stamp}.log'
    command = ['cmd.exe', '/c', str(build_bat), 'EndEditor', 'Win64', 'Development', f'-Project={PROJECT}'] + \
              [f'-Module={m}' for m in MODULES] + ['-WaitMutex', '-NoHotReloadFromIDE']
    with log.open('wb') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=3600).returncode
    (logs / 'latest.txt').write_text(str(log), encoding='utf-8')
    text = log.read_text(encoding='utf-8', errors='replace')
    binaries = PLUGIN / 'Binaries' / 'Win64'
    built = {m: (binaries / f'UE4Editor-{m}.dll').exists() for m in MODULES}
    result = {'exit_code': code, 'log': str(log), 'built': built}
    if code == 0 and all(built.values()):
        result['manifest'] = write_manifest(binaries)
    errors = [line for line in text.splitlines() if ': error' in line or 'error C' in line or 'ERROR:' in line]
    if errors:
        result['errors'] = errors[:40]
    print(text[-3000:])
    print(json.dumps(result, indent=2))
    return code if code else (0 if all(built.values()) else 1)


if __name__ == '__main__':
    raise SystemExit(main())
