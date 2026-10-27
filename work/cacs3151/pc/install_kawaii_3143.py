"""Create a Character System 3.14.3: put Young Sephiroth's KawaiiPhysics file into the game mod's compat folder.

  python install_kawaii_3143.py <compat folder>

compat_3143\\YoungSephirothKawaii.json (next to this script) goes into the compat folder. A different file of that name
already there is kept as YoungSephirothKawaii.json.before3143 first; the same file is left as it is.
"""
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = 'YoungSephirothKawaii.json'
EXPECTED = '176f39a3d51ad3bb1701fd8707011525'


def digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: install_kawaii_3143.py <compat folder>')
        return 2
    compat = Path(sys.argv[1])
    source = HERE / 'compat_3143' / NAME
    if not source.is_file():
        print(f'   FAILED: {source} is missing (tell Sandalphon)')
        return 1
    if digest(source) != EXPECTED:
        print(f'   FAILED: {source} is not the 3.14.3 file (tell Sandalphon)')
        return 1
    if not compat.is_dir():
        print(f'   FAILED: the compat folder {compat} was not found')
        return 1
    target = compat / NAME
    if target.is_file():
        if digest(target) == digest(source):
            print(f'   {NAME}: already in place')
            return 0
        backup = target.with_name(NAME + '.before3143')
        if not backup.exists():
            shutil.copy2(target, backup)
            print(f'   the {NAME} there is kept as {backup.name}')
    shutil.copy2(source, target)
    if digest(target) != digest(source):
        print(f'   FAILED: {NAME} was not copied whole')
        return 1
    print(f'   {NAME} in place: the coat kept out of his legs (leg colliders his legs\' size), every chain calmer when he runs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
