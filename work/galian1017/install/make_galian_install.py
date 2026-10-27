"""run_galian375_install.cmd from run_galian375_install.template: every md5 filled from the staged files and the bases.
    make_galian_install.py <stage dir: paks/ compat/ src/ mod/> <bases json> <out .cmd>
bases json: {"assets_utoc": md5 of the installed FullyPlayableVincentAssets_P.utoc, "shop_utoc": ..., "cpp": ..., "hpp": ...,
             "readme": ..., "build_dll": md5 of Tools\\RebirthSkelCompat\\build_dll.py}"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'run_galian375_install.template')
TAIL = r'''certutil -hashfile "%ONEOF_FILE%" MD5 2>nul | findstr /i %ONEOF_FIND% >nul
if not errorlevel 1 exit /b 0
for %%N in ("%ONEOF_FILE%") do echo    %%~nxN is not one this was made for>> "%STATUS%"
exit /b 1

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b'''


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def main(stage, bases_file, out):
    bases = json.load(open(bases_file))
    staged = {}
    for sub in ('paks', 'compat', 'src', 'mod'):
        for name in sorted(os.listdir(os.path.join(stage, sub))):
            staged['%s\\%s' % (sub, name)] = md5(os.path.join(stage, sub, name))
    want = ['paks\\%s.%s' % (n, e) for n in ('VincentGalian_P', 'FullyPlayableVincentAssets_P', 'zzVincentGunShop_P') for e in ('pak', 'ucas', 'utoc')] + \
           ['compat\\VincentGalian.json', 'src\\RebirthSkelCompat.cpp', 'src\\SkelCompatCore.hpp', 'mod\\README.txt']
    assert sorted(staged) == sorted(want), (sorted(staged), sorted(want))
    checks = '\n'.join('call :md5 "%%STAGE%%\\%s" %s || goto :badstage' % (k, staged[k]) for k in want)

    def installed(name, folder):
        return '\n'.join('call :md5 "%%%s%%\\%s.%s" %s || goto :failed' % (folder, name, e, staged['paks\\%s.%s' % (name, e)]) for e in ('pak', 'ucas', 'utoc'))
    t = open(TEMPLATE).read()
    fills = {
        '@ASSETS_BASE@': bases['assets_utoc'], '@ASSETS_NEW@': staged['paks\\FullyPlayableVincentAssets_P.utoc'],
        '@SHOP_BASE@': bases['shop_utoc'], '@SHOP_NEW@': staged['paks\\zzVincentGunShop_P.utoc'],
        '@CPP_BASE@': bases['cpp'], '@CPP_NEW@': staged['src\\RebirthSkelCompat.cpp'],
        '@HPP_BASE@': bases['hpp'], '@HPP_NEW@': staged['src\\SkelCompatCore.hpp'],
        '@README_BASE@': bases['readme'], '@README_NEW@': staged['mod\\README.txt'],
        '@BUILD_DLL@': bases['build_dll'],
        '@STAGE_CHECKS@': checks, '@STAGE_COUNT@': str(len(want)),
        '@GALIAN_UTOC@': staged['paks\\VincentGalian_P.utoc'], '@GALIAN_JSON@': staged['compat\\VincentGalian.json'],
        '@INSTALL_GALIAN_CHECKS@': installed('VincentGalian_P', 'VPAKS'),
        '@INSTALL_ASSETS_CHECKS@': installed('FullyPlayableVincentAssets_P', 'VPAKS'),
        '@INSTALL_SHOP_CHECKS@': installed('zzVincentGunShop_P', 'SHOPDIR'),
        '@ONEOF_TAIL@': TAIL,
    }
    for k, v in fills.items():
        assert k in t, k
        t = t.replace(k, v)
    assert '@' not in t.replace('@echo', ''), [line for line in t.split('\n') if '@' in line.replace('@echo', '')][:3]
    open(out, 'wb').write(t.replace('\r\n', '\n').replace('\n', '\r\n').encode('ascii'))
    print(out, md5(out), len(want), 'staged files')
    for k in want:
        print('  %-44s %s' % (k, staged[k]))


if __name__ == '__main__':
    main(*sys.argv[1:])
