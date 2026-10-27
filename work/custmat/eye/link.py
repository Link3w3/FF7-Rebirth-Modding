"""Runs Python in the user's editor through the Rebirth editor link (Saved/RebirthEditorLink) from the device shell.

    python3 link.py <code file> [timeout seconds]

Writes command.py with a fresh seq, waits for status.json to answer it, prints the status as JSON.
"""
import json
import os
import sys
import time

LINK = os.path.expanduser('~/mnt/FF7R2UProj/Saved/RebirthEditorLink')


def run(code, timeout=120.0):
    seq = int(time.time() * 1000)
    path = os.path.join(LINK, 'command.py')
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        f.write('# seq = %d\n' % seq + code)
    os.replace(path + '.tmp', path)
    end = time.time() + timeout
    while time.time() < end:
        try:
            with open(os.path.join(LINK, 'status.json'), encoding='utf-8') as f:
                s = json.load(f)
            if s.get('seq') == seq:
                return s
        except Exception:
            pass
        time.sleep(0.3)
    return {'seq': seq, 'ok': False, 'error': 'no answer in %.0f s (editor busy or closed?)' % timeout}


if __name__ == '__main__':
    code = open(sys.argv[1], encoding='utf-8').read()
    s = run(code, float(sys.argv[2]) if len(sys.argv) > 2 else 120.0)
    print(json.dumps(s, indent=1, default=str)[:20000])
