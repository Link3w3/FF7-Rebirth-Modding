"""Kawaii Dynamic Motions, step 4 of run_kawaii_dynamic_motions_install.cmd: runs make_kdm_example.py in an End editor
commandlet (the End editor closed: an open one would hold the assets) and waits for it. It makes Bahamut Fused
Sephiroth's example AnimBlueprint (/Game/KawaiiDynamicMotions/Examples/BahamutFusedSephiroth). The files next to this
script are checked against manifest.json first. When the script has finished and the editor does not exit within 3
minutes, it is stopped (the work is saved by then); after 45 minutes in all, too.
    run_kdm_example.py
Exit 0: made (the result says "done"); 1: not (it says why; the editor's log: build\\kdm_example_editor.log)."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
UE = r'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe'
PROJECT = r'C:\FF7R2UProj\End.uproject'
SCRIPT = os.path.join(HERE, 'make_kdm_example.py')
RESULT = r'C:\FF7R2UProj\Saved\KawaiiDynamicMotions\example_result.json'
BUILD = os.path.normpath(os.path.join(HERE, '..', 'build'))
LOG = os.path.join(BUILD, 'kdm_example_editor.log')
MOST_MINUTES = 45


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def read_result(started):
    try:
        if os.path.getmtime(RESULT) < started:
            return None
        with open(RESULT, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def main():
    for path in (UE, PROJECT, SCRIPT):
        if not os.path.isfile(path):
            print('   FAILED: %s is missing' % path)
            return 1
    manifest = json.load(open(os.path.join(HERE, 'manifest.json'), encoding='utf-8'))
    for rel, want in manifest['files'].items():
        path = os.path.join(HERE, *rel.split('/'))
        if not os.path.isfile(path) or md5(path) != want:
            print('   FAILED: %s is missing or not the file made for this (MD5; tell Sandalphon)' % path)
            return 1
    os.makedirs(BUILD, exist_ok=True)
    if os.path.exists(LOG):
        shutil.move(LOG, os.path.join(BUILD, 'kdm_example_editor_%s.log' % time.strftime('%Y%m%d_%H%M%S', time.localtime(os.path.getmtime(LOG)))))
    started = time.time()
    args = [UE, PROJECT, '-run=pythonscript', '-script=' + SCRIPT, '-unattended', '-nopause', '-nosplash', '-nosound', '-abslog=' + LOG]
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    print('   the editor is making it (in the background, no window; a few minutes)...', flush=True)
    finished_at = None
    while process.poll() is None:
        time.sleep(5)
        result = read_result(started)
        if finished_at is None and result and ('done' in result or 'error' in result):
            finished_at = time.time()
        if finished_at and time.time() - finished_at > 180:
            print('   the editor did not exit after the script finished: stopped')
            process.kill()
            break
        if time.time() - started > MOST_MINUTES * 60:
            print('   TIMEOUT after %d minutes: the editor was stopped' % MOST_MINUTES)
            process.kill()
            break
    process.wait()
    result = read_result(started)
    if not result:
        print('   FAILED: the editor script left no result (the editor stopped early? build\\kdm_example_editor.log)')
        return 1
    if 'error' in result:
        lines = [line for line in result['error'].strip().splitlines() if line.strip()]
        print('   FAILED: ' + ' | '.join(lines[-2:]))
        return 1
    if 'done' not in result:
        print('   FAILED: the editor script stopped after "%s" (build\\kdm_example_editor.log)' % (result.get('steps') or ['its start'])[-1])
        return 1
    for line in str(result.get('animations', '')).strip().splitlines():
        if line.strip():
            print('   ' + line.strip())
    print('   ' + str(result.get('anim_blueprint', '')).strip().splitlines()[0])
    print('   made in %.0f s: %s' % (time.time() - started, result['done']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
