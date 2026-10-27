"""Take the post process materials out of the "Rebirth Menu Day" preview profile (Config\\DefaultEditor.ini), so the
model editors open even without the editor plugin's post process material row (run_build_blendable_fix.cmd runs this
only when that build failed). The profile keeps its lights, sky and exposure; the game's tonemapper is what goes.
A copy of the ini goes to _mod_backups first.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(r'C:\FF7R2UProj')
INI = PROJECT / 'Config' / 'DefaultEditor.ini'
PROFILE = 'ProfileName="Rebirth Menu Day"'
KEY = 'WeightedBlendables='


def drop_field(line: str) -> str:
    at = line.find(KEY)
    if at < 0:
        return line
    i = at + len(KEY)
    if i >= len(line) or line[i] != '(':
        return line
    depth = 0
    quote = False
    for j in range(i, len(line)):
        c = line[j]
        if c == '"':
            quote = not quote
        elif not quote and c == '(':
            depth += 1
        elif not quote and c == ')':
            depth -= 1
            if depth == 0:
                start = at - 1 if at > 0 and line[at - 1] == ',' else at
                end = j + 1
                if start == at and end < len(line) and line[end] == ',':
                    end += 1
                return line[:start] + line[end:]
    return line


def main() -> int:
    text = INI.read_text(encoding='utf-8-sig')
    lines = text.splitlines(keepends=True)
    changed = 0
    for n, line in enumerate(lines):
        if PROFILE in line and KEY in line:
            new = drop_field(line)
            if new != line:
                lines[n] = new
                changed += 1
    if not changed:
        print(f'{INI}: the profile has no post process materials; nothing changed')
        return 0
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = PROJECT / '_mod_backups' / f'preview_blendable_{stamp}'
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INI, backup / INI.name)
    INI.write_text(''.join(lines), encoding='utf-8')
    print(f'{INI}: post process materials taken out of the Rebirth Menu Day profile (copy in {backup})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
