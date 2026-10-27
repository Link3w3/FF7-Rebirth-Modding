"""Where the game-material tools find things: the shader compiler (dxc), the engine's shader sources, the third-party
Python packages that ship with these tools, and a work folder. Each can be set explicitly (set_*), which the editor
side does from the project, and offline tests do with their own copies."""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)                     # rebirth_fx
THIRD_PARTY = os.path.join(PACKAGE, 'third_party', 'py37_win64')

_dxc = None
_dxc_env = None
_engine_shaders = None
_work = None


def vendor():
    """Puts the bundled packages (numpy, Pillow, lz4, UnityPy...) on sys.path, on Windows."""
    if sys.platform.startswith('win') and os.path.isdir(THIRD_PARTY) and THIRD_PARTY not in sys.path:
        sys.path.insert(0, THIRD_PARTY)


def set_dxc(path, env=None):
    global _dxc, _dxc_env
    _dxc, _dxc_env = path, env


def _version_key(path):
    parts = []
    for p in path.replace('\\', '/').split('/'):
        if p[:1].isdigit():
            parts.append(tuple(int(x) for x in p.split('.') if x.isdigit()))
    return parts


def find_dxc():
    """The newest dxc.exe of the Windows SDK (Windows Kits 10), or one next to these tools (third_party/dxc)."""
    own = os.path.join(PACKAGE, 'third_party', 'dxc', 'dxc.exe')
    if os.path.isfile(own):
        return own
    found = []
    for root in (os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('ProgramFiles', r'C:\Program Files')):
        found += glob.glob(os.path.join(root, 'Windows Kits', '10', 'bin', '*', 'x64', 'dxc.exe'))
    found = [f for f in found if os.path.isfile(os.path.join(os.path.dirname(f), 'dxcompiler.dll'))]
    if not found:
        return None
    return sorted(found, key=_version_key)[-1]


def dxc():
    global _dxc
    if _dxc is None:
        _dxc = find_dxc()
        if _dxc is None:
            raise RuntimeError('No shader compiler found: these tools use dxc.exe from the Windows 10/11 SDK (Visual Studio '
                               'Installer > Individual components > Windows 11 SDK), or put dxc.exe, dxcompiler.dll and '
                               'dxil.dll in %s' % os.path.join(PACKAGE, 'third_party', 'dxc'))
    return _dxc


def run_dxc(args, cwd=None):
    kwargs = dict(capture_output=True, text=True, cwd=cwd, env=_dxc_env)
    if sys.platform.startswith('win'):
        kwargs['creationflags'] = 0x08000000        # CREATE_NO_WINDOW: no console flashing up per compile
    r = subprocess.run([dxc()] + list(args), **kwargs)
    return r.returncode, r.stdout, r.stderr


def set_engine_shaders(path):
    global _engine_shaders
    _engine_shaders = path


def engine_shaders():
    """The engine's Shaders folder (Private, Public, Shared): the editor's own copy."""
    global _engine_shaders
    if _engine_shaders is None:
        try:
            import unreal
            _engine_shaders = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_dir()), 'Shaders')
        except ImportError:
            raise RuntimeError('set the engine shader folder (env.set_engine_shaders) outside the editor')
    return _engine_shaders


def set_work(path):
    global _work
    _work = path


def work(*parts):
    global _work
    if _work is None:
        try:
            import unreal
            _work = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthGameMaterials')
        except ImportError:
            _work = os.path.join(os.getcwd(), 'RebirthGameMaterials')
    path = os.path.join(_work, *parts)
    return path
