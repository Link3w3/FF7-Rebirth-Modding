"""Create a Character System 3.14.0: put Young Sephiroth's KawaiiPhysics file into the game mod's compat folder.

  python install_kawaii_3140.py <compat folder>

compat_3140\\YoungSephirothKawaii.json (next to this script) goes into the compat folder. A different file of that name
already there is kept as YoungSephirothKawaii.json.before3140 first; the same file is left as it is.
"""
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = 'YoungSephirothKawaii.json'


def digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: install_kawaii_3140.py <compat folder>')
        return 2
    compat = Path(sys.argv[1])
    source = HERE / 'compat_3140' / NAME
    if not source.is_file():
        print(f'   FAILED: {source} is missing (tell Sandalphon)')
        return 1
    if not compat.is_dir():
        print(f'   FAILED: the compat folder {compat} was not found')
        return 1
    target = compat / NAME
    if target.is_file():
        if digest(target) == digest(source):
            print(f'   {NAME}: already in place')
            return 0
        backup = target.with_name(NAME + '.before3140')
        if not backup.exists():
            shutil.copy2(target, backup)
            print(f'   the {NAME} there is kept as {backup.name}')
    shutil.copy2(source, target)
    if digest(target) != digest(source):
        print(f'   FAILED: {NAME} was not copied whole')
        return 1
    print(f'   {NAME} in place: Young Sephiroth\'s hair, coat, collar and wing swing with KawaiiPhysics (his model without BNMs, its KDI kept)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
