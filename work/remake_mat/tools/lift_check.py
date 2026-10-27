"""The lifter's check: a game shader and its lifted HLSL compiled again (Microsoft's compiler under Wine) run side by side
on the same random inputs (both translated to C++ by dxbc2cpp.py); every output must agree.

    lift_check.py [-n cases] [--strict] <shader.asm> [<shader.asm> ...]

Prints per shader: the instruction counts, the largest difference per output and the cases where only one discarded."""
import os
import re
import subprocess
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxbc2cpp
import dxbc2hlsl

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = '/work/rmsurf/harness'
WINE = ['/usr/lib/wine/wine64', '/work/fxcw/fxcw.exe', 'Z:\\work\\fxcw\\d3dcompiler_47.dll']
ENV = dict(os.environ, WINEPREFIX='/tmp/wpfx', WINEDEBUG='-all', WINEDLLOVERRIDES='d3dcompiler_47=n')


def winpath(p):
    return 'Z:' + os.path.abspath(p).replace('/', '\\')


def fxc(hlsl_path, target, out_dxbc, flags=None):
    args = WINE + [winpath(hlsl_path), target, 'main', winpath(out_dxbc)]
    if flags is not None:
        args.append('%x' % flags)
    p = subprocess.run(args, capture_output=True, text=True, env=ENV)
    if 'FXC OK' not in p.stdout:
        raise RuntimeError('fxc failed:\n' + p.stdout[-4000:] + p.stderr[-2000:])
    asm = out_dxbc[:-5] + '.asm'
    p = subprocess.run(WINE + ['--disasm', winpath(out_dxbc), winpath(asm), '80'], capture_output=True, text=True, env=ENV)
    return open(asm, 'rb').read().replace(b'\x00', b'').decode('latin-1')


DRIVER = r'''
#include <random>
#include <cstdio>
#include <cstring>
#include <cmath>
static std::mt19937_64 rng;
static double U(double a, double b) { return a + (b - a) * std::uniform_real_distribution<double>(0, 1)(rng); }
static uint32_t fbits(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
int main(int argc, char** argv)
{
    const int N = argc > 1 ? atoi(argv[1]) : 200;
    double maxd[10][4] = {};
    int nanmis[10][4] = {};
    int discard_mis = 0, discards = 0;
    for (int k = 0; k < N; ++k)
    {
        rng.seed(1000 + k);
        DXIO a;
        for (int r = 0; r < 40; ++r)
            for (int c = 0; c < 4; ++c)
            {
                const double v = U(-1.5, 1.5);
                a.v[r][c] = LF(D(v, U(-0.01, 0.01), U(-0.01, 0.01)));
            }
        // SV_Position: a pixel, its depth and 1/w
        a.v[POSREG][0] = LF(D(std::floor(U(0, 1920)) + 0.5, 1.0, 0.0));
        a.v[POSREG][1] = LF(D(std::floor(U(0, 1080)) + 0.5, 0.0, 1.0));
        a.v[POSREG][2] = LF(D(U(0.001, 1.0), 0, 0));
        a.v[POSREG][3] = LF(D(U(0.01, 1.0), 0, 0));
        a.v[FACEREG][0] = LU(U(0, 1) < 0.8 ? 0xffffffffu : 0u);
        for (int b = 0; b < 16; ++b)
        {
            a.cb[b].resize(256);
            for (auto& row : a.cb[b])
                for (int c = 0; c < 4; ++c)
                {
                    const double x = U(0, 1);
                    // most lanes floats; some small integers (flags, indices); some 0 and 1
                    row[c] = x < 0.75 ? fbits((float)U(-2.0, 2.0)) : x < 0.85 ? (uint32_t)(int)U(0, 64) : x < 0.93 ? 0u : fbits(1.0f);
                }
        }
        for (int t = 0; t < 128; ++t) a.tex[t] = 0x1234567ULL * (t + 1) + k * 7919ULL;
        for (int s = 0; s < 16; ++s) a.samp[s] = s + 1;
        DXIO b = a;
        shader_orig(a);
        shader_lift(b);
        if (a.discarded != b.discarded) { ++discard_mis; continue; }
        if (a.discarded) { ++discards; continue; }
        for (int o = 0; o < 10; ++o)
            for (int c = 0; c < 4; ++c)
            {
                const double x = a.o[o][c].f.v, y = b.o[o][c].f.v;
                if (std::isnan(x) || std::isnan(y)) { if (std::isnan(x) != std::isnan(y)) ++nanmis[o][c]; continue; }
                const double d = std::fabs(x - y) / std::max(1.0, std::fabs(x));
                if (d > maxd[o][c]) maxd[o][c] = d;
            }
    }
    double worst = 0;
    for (int o = 0; o < 10; ++o)
        for (int c = 0; c < 4; ++c)
            if (maxd[o][c] > worst) worst = maxd[o][c];
    printf("cases %d discards %d discard_mismatch %d worst %.3g\n", N, discards, discard_mis, worst);
    for (int o = 0; o < 10; ++o)
    {
        bool any = false;
        for (int c = 0; c < 4; ++c) any |= maxd[o][c] > 1e-5 || nanmis[o][c];
        if (any)
            printf("  o%d: %.3g %.3g %.3g %.3g  nan-mismatch %d %d %d %d\n", o, maxd[o][0], maxd[o][1], maxd[o][2], maxd[o][3],
                   nanmis[o][0], nanmis[o][1], nanmis[o][2], nanmis[o][3]);
    }
    return 0;
}
'''


def check(asm_path, n=200, strict=False, work=None):
    work = work or tempfile.mkdtemp(prefix='lift_', dir='/tmp/scratch')
    src = open(asm_path, encoding='latin-1').read()
    hl = dxbc2hlsl.wrapper(src)
    hp = os.path.join(work, 'lift.hlsl')
    open(hp, 'w').write(hl)
    target = re.search(r'^(ps|vs)_5_0', src.replace('\x00', ''), re.M).group(0)
    asm2 = fxc(hp, target, os.path.join(work, 'lift.dxbc'), 0x2000 if strict else None)
    L = dxbc2hlsl.Lifter(src)
    pos = next((int(r[3]) for r in L.input_sig if r[4] == 'POS'), 39)
    face = next((int(r[3]) for r in L.input_sig if r[4] == 'FFACE'), 38)
    cpp = ['#include "dxbc_cpu.hpp"', '#define POSREG %d' % pos, '#define FACEREG %d' % face,
           dxbc2cpp.translate(src, 'shader_orig'), dxbc2cpp.translate(asm2, 'shader_lift'), DRIVER]
    cp = os.path.join(work, 'check.cpp')
    open(cp, 'w').write('\n'.join(cpp))
    exe = os.path.join(work, 'check')
    p = subprocess.run(['g++', '-std=c++17', '-O1', '-w', '-I' + HERE, '-I' + HARNESS, cp, '-o', exe], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('g++ failed:\n' + p.stderr[-4000:])
    p = subprocess.run([exe, str(n)], capture_output=True, text=True)
    count = lambda s: len([l for l in s.splitlines() if re.match(r'^\s*[a-z_0-9]+(\([^)]*\))*\s', l) and not l.strip().startswith(('dcl_', 'ps_', 'vs_', '//'))])
    return {'orig_instr': count(src.replace('\x00', '')), 'lift_instr': count(asm2), 'result': p.stdout.strip(), 'work': work}


if __name__ == '__main__':
    args = sys.argv[1:]
    n = 200
    strict = False
    if '-n' in args:
        i = args.index('-n'); n = int(args[i + 1]); del args[i:i + 2]
    if '--strict' in args:
        args.remove('--strict'); strict = True
    for a in args:
        try:
            r = check(a, n, strict)
            print('%s: %d -> %d instructions; %s' % (a, r['orig_instr'], r['lift_instr'], r['result']))
        except Exception as ex:
            print('%s: FAILED %s' % (a, ex))
