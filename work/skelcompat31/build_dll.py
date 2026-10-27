"""Build RebirthSkelCompat\\dlls\\main.dll against the installed UE4SS 3.0.1 c0a8d4c SDK.

Same compiler, flags and include order as the RebirthSkeletonObserver build that already
compiled and ran against this loader. Verifies the result before anything is installed:
  * exports are exactly start_mod / uninstall_mod
  * every UE4SS.dll import exists in the installed UE4SS.dll (no forwarders)

  python build_dll.py                 build + verify
  python build_dll.py --install       build + verify + install into the game's UE4SS Mods folder
  python build_dll.py --pack-headers  also zip SDK/toolchain headers to out\\sdk-headers.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE / 'src'
SOURCE = SRC_DIR / 'RebirthSkelCompat.cpp'
MOD_FILES = HERE / 'mod'

MATERIALS = Path(r'C:\Users\Kade\Documents\Codex\2026-09-12\create-an-image-of-2\work\rebirth-materials')
SDK = MATERIALS / 'ue4ss-stage' / 'existing-loader-c0a8d4c'
SDK_SRC = SDK / 'source'
UE4SS_LIB = SDK / 'native-sdk-imports' / 'UE4SS.lib'
OBSERVER = MATERIALS / 'retail-observer-c0a8'
SHIMS = OBSERVER / 'include-shims'
DEPS = OBSERVER / 'dependency-headers'

GAME = Path(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH')
UE4SS_DIR = GAME / 'End' / 'Binaries' / 'Win64' / 'ue4ss'
UE4SS_DLL = UE4SS_DIR / 'UE4SS.dll'
MOD_DIR = UE4SS_DIR / 'Mods' / 'RebirthSkelCompat'

VS_ROOTS = [Path(r'C:\Program Files\Microsoft Visual Studio\2022') / e for e in ('Community', 'Professional', 'Enterprise', 'BuildTools')]
PREFERRED_MSVC = '14.44.35207'
KIT = Path(r'C:\Program Files (x86)\Windows Kits\10')
KITVER = '10.0.26100.0'

ENGINE_SOURCE = Path(r'C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Source')
ENGINE_REFERENCE_DIRS = [
    'Runtime/Engine/Classes/Animation', 'Runtime/Engine/Classes/Engine', 'Runtime/Engine/Classes/Interfaces',
    'Runtime/Engine/Classes/EdGraph', 'Runtime/Engine/Public/Animation', 'Runtime/Engine/Public/ReferenceSkeleton.h',
    'Runtime/Engine/Public/BoneContainer.h', 'Runtime/CoreUObject/Public', 'Runtime/AssetRegistry/Public', 'Runtime/Json/Public',
    'Runtime/Core/Public/Misc', 'Runtime/Core/Public/Containers', 'Editor/UnrealEd/Public/Kismet2', 'Editor/UnrealEd/Public/FileHelpers.h',
    'Editor/UnrealEd/Public/PackageTools.h', 'Editor/UnrealEd/Public/ObjectTools.h', 'Editor/UnrealEd/Classes/Factories/Factory.h',
    'Editor/BlueprintGraph/Classes/EdGraphSchema_K2.h', 'Developer/AssetTools/Public/AssetTypeCategories.h',
]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def row(path: Path) -> dict:
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


# --------------------------------------------------------------------------------------
# Minimal PE reader (no third-party modules needed)
# --------------------------------------------------------------------------------------
class PeImage:
    def __init__(self, path: Path):
        self.data = Path(path).read_bytes()
        d = self.data
        if d[:2] != b'MZ':
            raise ValueError(f'{path}: not a PE file')
        nt = struct.unpack_from('<I', d, 0x3C)[0]
        if d[nt:nt + 4] != b'PE\0\0':
            raise ValueError(f'{path}: bad NT signature')
        coff = nt + 4
        self.machine, sections, _, _, _, optional_size, _ = struct.unpack_from('<HHIIIHH', d, coff)
        optional = coff + 20
        if struct.unpack_from('<H', d, optional)[0] != 0x20B:
            raise ValueError(f'{path}: not PE32+')
        count = struct.unpack_from('<I', d, optional + 108)[0]
        self.dirs = [struct.unpack_from('<II', d, optional + 112 + 8 * i) for i in range(count)]
        self.sections = []
        table = optional + optional_size
        for i in range(sections):
            _, vsize, va, raw_size, raw_ptr = struct.unpack_from('<8sIIII', d, table + 40 * i)
            self.sections.append((va, max(vsize, raw_size), raw_ptr))

    def offset(self, rva: int) -> int:
        for va, size, raw in self.sections:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError(f'RVA {rva:#x} outside sections')

    def cstr(self, rva: int) -> str:
        start = self.offset(rva)
        return self.data[start:self.data.index(b'\0', start)].decode('ascii')

    def exports(self) -> dict:
        rva, size = self.dirs[0]
        if not rva:
            return {}
        _, _, _, _, _, base, functions, names, function_rva, name_rva, ordinal_rva = struct.unpack_from('<IIHHIIIIIII', self.data, self.offset(rva))
        result = {}
        for i in range(names):
            name = self.cstr(struct.unpack_from('<I', self.data, self.offset(name_rva + 4 * i))[0])
            index = struct.unpack_from('<H', self.data, self.offset(ordinal_rva + 2 * i))[0]
            target = struct.unpack_from('<I', self.data, self.offset(function_rva + 4 * index))[0]
            result[name] = {'ordinal': base + index, 'rva': target, 'forwarder': rva <= target < rva + size}
        return result

    def imports(self) -> list:
        rva, _ = self.dirs[1]
        result = []
        if not rva:
            return result
        at = self.offset(rva)
        while True:
            original, _, _, name, first = struct.unpack_from('<IIIII', self.data, at)
            if not (original or name or first):
                break
            module = self.cstr(name)
            thunk = self.offset(original or first)
            while True:
                entry = struct.unpack_from('<Q', self.data, thunk)[0]
                if not entry:
                    break
                if entry >> 63:
                    result.append({'module': module, 'name': None, 'ordinal': entry & 0xFFFF})
                else:
                    result.append({'module': module, 'name': self.cstr((entry & 0x7FFFFFFF) + 2), 'ordinal': None})
                thunk += 8
            at += 20
        return result


# --------------------------------------------------------------------------------------
# Toolchain
# --------------------------------------------------------------------------------------
def find_msvc() -> Path:
    candidates = []
    for root in VS_ROOTS:
        tools = root / 'VC' / 'Tools' / 'MSVC'
        if tools.is_dir():
            candidates += [p for p in tools.iterdir() if (p / 'bin' / 'Hostx64' / 'x64' / 'cl.exe').is_file()]
    if not candidates:
        raise SystemExit('No Visual Studio 2022 x64 compiler found')
    preferred = [p for p in candidates if p.name == PREFERRED_MSVC]
    return preferred[0] if preferred else sorted(candidates, key=lambda p: [int(x) for x in p.name.split('.')])[-1]


def include_dirs(msvc: Path) -> list[Path]:
    dirs = [SHIMS, DEPS / 'fmt-10.2.1' / 'include', DEPS / 'zydis-4.1.0' / 'include', DEPS / 'zycore-zydis4.1.0-gitlink' / 'include',
            SDK_SRC / 'UE4SS' / 'include', SDK_SRC / 'UE4SS' / 'generated_include']
    for package in sorted((SDK_SRC / 'deps' / 'first').iterdir()):
        for relative in ('include', 'generated_include'):
            if (package / relative).is_dir():
                dirs.append(package / relative)
    dirs += [SDK_SRC / 'deps' / 'first' / 'Unreal' / 'include' / 'Unreal', SDK_SRC / 'deps' / 'first' / 'Unreal' / 'include' / 'Unreal' / 'Core',
             msvc / 'include', KIT / 'Include' / KITVER / 'ucrt', KIT / 'Include' / KITVER / 'shared',
             KIT / 'Include' / KITVER / 'um', KIT / 'Include' / KITVER / 'winrt']
    return dirs


def compile_and_link(out: Path, msvc: Path) -> dict:
    cl = msvc / 'bin' / 'Hostx64' / 'x64' / 'cl.exe'
    link = cl.with_name('link.exe')
    for required in (SOURCE, SRC_DIR / 'SkelCompatCore.hpp', UE4SS_LIB, SHIMS / 'GUI' / 'GUI.hpp', SDK_SRC / 'UE4SS' / 'include' / 'Mod' / 'CppUserModBase.hpp'):
        if not required.exists():
            raise SystemExit(f'Missing build input: {required}')
    for name in ('RebirthSkelCompat.cpp', 'SkelCompatCore.hpp'):
        shutil.copy2(SRC_DIR / name, out / name)
    args = ['/nologo', '/c', '/MD', '/std:c++20', '/Zc:__cplusplus', '/Zc:preprocessor', '/EHa', '/O2', '/W4', '/Zi',
            '/DWIN32', '/D_WINDOWS', '/DNDEBUG', '/D_ITERATOR_DEBUG_LEVEL=0', '/DUE_BUILD_SHIPPING=1', '/DUE_GAME=1',
            '/DPLATFORM_WINDOWS=1', '/DPLATFORM_MICROSOFT=1', '/DOVERRIDE_PLATFORM_HEADER_NAME=Windows',
            '/DUBT_COMPILED_PLATFORM=Win64', '/DUNICODE', '/D_UNICODE', '/utf-8',
            '/FoRebirthSkelCompat.obj', '/FdRebirthSkelCompat.pdb']
    args += [f'/I"{d}"' for d in include_dirs(msvc)]
    args.append('RebirthSkelCompat.cpp')
    (out / 'compile.rsp').write_text('\n'.join(args), encoding='utf-8')
    env = os.environ.copy()
    env['PATH'] = str(cl.parent) + os.pathsep + str(KIT / 'bin' / KITVER / 'x64') + os.pathsep + env.get('PATH', '')
    result = {'compiler': str(cl)}
    with (out / 'compile.log').open('wb') as log:
        result['compile_exit_code'] = subprocess.run([str(cl), '@compile.rsp'], cwd=out, env=env, stdout=log,
                                                     stderr=subprocess.STDOUT, timeout=600).returncode
    if result['compile_exit_code'] != 0:
        return result
    link_args = ['/NOLOGO', '/DLL', '/MACHINE:X64', '/INCREMENTAL:NO', '/OPT:REF', '/OPT:ICF', '/DEBUG:FULL',
                 '/OUT:main.dll', '/IMPLIB:main.lib', '/PDB:main.pdb', 'RebirthSkelCompat.obj', f'"{UE4SS_LIB}"',
                 'kernel32.lib', f'/LIBPATH:"{msvc / "lib" / "x64"}"', f'/LIBPATH:"{KIT / "Lib" / KITVER / "ucrt" / "x64"}"',
                 f'/LIBPATH:"{KIT / "Lib" / KITVER / "um" / "x64"}"']
    (out / 'link.rsp').write_text('\n'.join(link_args), encoding='utf-8')
    with (out / 'link.log').open('wb') as log:
        result['link_exit_code'] = subprocess.run([str(link), '@link.rsp'], cwd=out, env=env, stdout=log,
                                                  stderr=subprocess.STDOUT, timeout=300).returncode
    return result


def verify(dll: Path) -> dict:
    image = PeImage(dll)
    loader = PeImage(UE4SS_DLL).exports()
    exports = sorted(image.exports())
    imports = image.imports()
    missing = [i['name'] for i in imports if i['module'].lower() == 'ue4ss.dll' and (i['name'] not in loader or loader[i['name']]['forwarder'])]
    modules = sorted({i['module'] for i in imports})
    report = {'exports': exports, 'imported_modules': modules,
              'ue4ss_imports': sorted(i['name'] for i in imports if i['module'].lower() == 'ue4ss.dll'),
              'missing_in_installed_ue4ss': missing, 'machine': hex(image.machine)}
    report['ok'] = exports == ['start_mod', 'uninstall_mod'] and not missing and image.machine == 0x8664 and bool(report['ue4ss_imports'])
    return report


# --------------------------------------------------------------------------------------
# Install / header snapshot
# --------------------------------------------------------------------------------------
def install(dll: Path, stamp: str) -> dict:
    if not UE4SS_DLL.is_file():
        raise SystemExit(f'UE4SS not found at {UE4SS_DLL}')
    target = MOD_DIR / 'dlls' / 'main.dll'
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'mod_dir': str(MOD_DIR)}
    if target.exists():
        backup = target.with_name(f'main.dll.bak-{stamp}')
        try:
            # A DLL the running game has loaded can be renamed (not overwritten); the game keeps the
            # old image until it restarts and loads the new main.dll.
            os.replace(target, backup)
            receipt['previous_moved_aside'] = True
        except OSError:
            shutil.copy2(target, backup)
        receipt['previous_backup'] = str(backup)
    shutil.copy2(dll, target)
    pdb = dll.with_suffix('.pdb')
    if pdb.exists():
        shutil.copy2(pdb, target.with_suffix('.pdb'))
    (MOD_DIR / 'compat').mkdir(exist_ok=True)
    if not (MOD_DIR / 'enabled.txt').exists():
        (MOD_DIR / 'enabled.txt').write_bytes(b'')
    for name in ('README.txt',):
        if (MOD_FILES / name).is_file():
            shutil.copy2(MOD_FILES / name, MOD_DIR / name)
    example = MOD_FILES / 'compat' / 'example.json.txt'
    if example.is_file():
        shutil.copy2(example, MOD_DIR / 'compat' / example.name)
    receipt['installed'] = row(target)
    return receipt


HEADER_SUFFIXES = {'.h', '.hpp', '.hh', '.hxx', '.inl', '.ipp', '.inc', '.tlh', '.tli', '.version'}


def pack_headers(msvc: Path, destination: Path) -> dict:
    roots = [('shims', SHIMS)]
    for name in ('fmt-10.2.1', 'zydis-4.1.0', 'zycore-zydis4.1.0-gitlink'):
        roots.append((f'deps/{name}', DEPS / name / 'include'))
    roots += [('ue4ss/UE4SS/include', SDK_SRC / 'UE4SS' / 'include'), ('ue4ss/UE4SS/generated_include', SDK_SRC / 'UE4SS' / 'generated_include')]
    for package in sorted((SDK_SRC / 'deps' / 'first').iterdir()):
        for relative in ('include', 'generated_include'):
            if (package / relative).is_dir():
                roots.append((f'ue4ss/deps/first/{package.name}/{relative}', package / relative))
    roots += [('msvc/include', msvc / 'include'), ('kits/ucrt', KIT / 'Include' / KITVER / 'ucrt'),
              ('kits/shared', KIT / 'Include' / KITVER / 'shared'), ('kits/um', KIT / 'Include' / KITVER / 'um')]
    for relative in ENGINE_REFERENCE_DIRS:
        roots.append((f'engine/{relative}', ENGINE_SOURCE / relative))
    roots.append(('engine/Build.version', ENGINE_SOURCE.parent / 'Build' / 'Build.version'))
    counts = {}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for label, root in roots:
            count = 0
            if root.is_file():
                archive.write(root, label)
                count = 1
            elif root.is_dir():
                for path in root.rglob('*'):
                    if not path.is_file():
                        continue
                    if label == 'msvc/include' or path.suffix.lower() in HEADER_SUFFIXES:
                        archive.write(path, f'{label}/{path.relative_to(root).as_posix()}')
                        count += 1
            counts[label] = count
        archive.writestr('manifest.json', json.dumps({'msvc': str(msvc), 'kit': KITVER, 'roots': counts}, indent=1))
    return {'zip': str(destination), 'bytes': destination.stat().st_size, 'roots': counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--install', action='store_true', help='install the verified DLL into the game UE4SS Mods folder')
    parser.add_argument('--pack-headers', action='store_true', help='zip SDK/toolchain headers into out\\sdk-headers.zip')
    parser.add_argument('--no-build', action='store_true', help='skip the build (use with --pack-headers)')
    options = parser.parse_args()

    msvc = find_msvc()
    receipt = {'schema': 1, 'msvc': str(msvc)}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    status = 0
    if not options.no_build:
        out = HERE / 'build' / stamp
        out.mkdir(parents=True)
        receipt['output'] = str(out)
        receipt.update(compile_and_link(out, msvc))
        dll = out / 'main.dll'
        if receipt.get('link_exit_code') == 0 and dll.is_file():
            receipt['verification'] = verify(dll)
            receipt['candidate'] = row(dll)
            if receipt['verification']['ok'] and options.install:
                receipt['install'] = install(dll, stamp)
        ok = receipt.get('verification', {}).get('ok', False)
        receipt['status'] = 'OK' if ok else 'FAILED'
        status = 0 if ok else 1
        (out / 'BuildResult.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        latest = HERE / 'build' / 'latest.txt'
        latest.write_text(str(out), encoding='utf-8')
        if receipt.get('compile_exit_code', 0) != 0:
            sys.stdout.write((out / 'compile.log').read_text(encoding='utf-8', errors='replace')[-6000:])
        elif receipt.get('link_exit_code', 0) != 0:
            sys.stdout.write((out / 'link.log').read_text(encoding='utf-8', errors='replace')[-4000:])
    if options.pack_headers:
        receipt['headers'] = pack_headers(msvc, HERE / 'out' / 'sdk-headers.zip')
    print(json.dumps({k: receipt[k] for k in receipt if k in ('status', 'output', 'compile_exit_code', 'link_exit_code', 'verification', 'install', 'headers')}, indent=2))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
