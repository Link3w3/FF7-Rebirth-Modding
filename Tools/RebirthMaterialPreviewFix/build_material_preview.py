"""Rebuild the RebirthMaterialPreview editor plugin (C:\\FF7R2UProj\\Plugins\\RebirthMaterialPreview) with
RebirthEngineV5's UnrealBuildTool. Only that module is compiled (-Module), End's own modules are untouched.
The current DLL/PDB are backed up first and put back if the build fails.

  python build_material_preview.py    (refuses while UE4Editor.exe runs)
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = Path(r'C:\RebirthEngine\RebirthEngineV5\Windows')
PROJECT = Path(r'C:\FF7R2UProj\End.uproject')
PLUGIN = PROJECT.parent / 'Plugins' / 'RebirthMaterialPreview'
MODULE = 'RebirthMaterialPreview'
BINARIES = PLUGIN / 'Binaries' / 'Win64'
FILES = [f'UE4Editor-{MODULE}.dll', f'UE4Editor-{MODULE}.pdb', 'UE4Editor.modules']


def editor_running() -> bool:
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UE4Editor.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True).stdout
    return 'UE4Editor.exe' in listing


def write_manifest() -> str:
    # -Module builds do not write UE4Editor.modules; the editor only loads modules whose BuildId matches the engine.
    engine = json.loads((ENGINE / 'Engine' / 'Binaries' / 'Win64' / 'UE4Editor.modules').read_text(encoding='utf-8-sig'))
    manifest = BINARIES / 'UE4Editor.modules'
    wanted = {'BuildId': engine['BuildId'], 'Modules': {MODULE: f'UE4Editor-{MODULE}.dll'}}
    try:
        current = json.loads(manifest.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        current = None
    if current != wanted:
        manifest.write_text(json.dumps(wanted, indent=2).replace('\n', '\r\n') + '\r\n', encoding='utf-8')
        return f'wrote {manifest} (BuildId {wanted["BuildId"]})'
    return f'{manifest} already current'


def main() -> int:
    result: dict = {'status': 'started'}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = HERE / 'build'
    out.mkdir(parents=True, exist_ok=True)
    try:
        if editor_running():
            result['status'] = 'refused: UE4Editor.exe is running, close the End editor first'
            return 2
        build_bat = ENGINE / 'Engine' / 'Build' / 'BatchFiles' / 'Build.bat'
        for required in (build_bat, PROJECT, PLUGIN / 'RebirthMaterialPreview.uplugin'):
            if not required.exists():
                result['status'] = f'missing: {required}'
                return 2
        backup = HERE / 'backup' / stamp
        backup.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            if (BINARIES / name).exists():
                shutil.copy2(BINARIES / name, backup / name)
        result['backup'] = str(backup)
        log = out / f'ubt-{stamp}.log'
        command = ['cmd.exe', '/c', str(build_bat), 'EndEditor', 'Win64', 'Development', f'-Project={PROJECT}',
                   f'-Module={MODULE}', '-WaitMutex', '-NoHotReloadFromIDE']
        with log.open('wb') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=3600).returncode
        text = log.read_text(encoding='utf-8', errors='replace')
        result['log'] = str(log)
        result['exit_code'] = code
        errors = [line for line in text.splitlines() if ': error' in line or 'error C' in line or 'ERROR:' in line]
        if errors:
            result['errors'] = errors[:40]
        dll = BINARIES / f'UE4Editor-{MODULE}.dll'
        if code == 0 and dll.exists():
            result['manifest'] = write_manifest()
            result['dll'] = {'path': str(dll), 'bytes': dll.stat().st_size,
                             'modified': datetime.fromtimestamp(dll.stat().st_mtime, timezone.utc).isoformat()}
            result['status'] = 'OK'
        else:
            for name in FILES:
                if (backup / name).exists():
                    shutil.copy2(backup / name, BINARIES / name)
            result['status'] = 'FAILED: previous DLL put back'
        result['log_tail'] = text[-2500:]
        return 0 if result['status'] == 'OK' else 1
    except Exception as error:  # report everything to the result file
        result['status'] = f'FAILED: {type(error).__name__}: {error}'
        return 1
    finally:
        (out / 'latest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
