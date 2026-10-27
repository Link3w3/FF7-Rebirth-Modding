"""Run a game-format (zen) Niagara package's particle scripts in the VM interpreter (nvmrun): spawn N particles,
update them for a few frames, and print the particle attributes. For checking converted effects (and reading what the
game's own effects compute) without the game.

    nsim.py <package> <emitter export index> [--spawn N] [--frames F] [--dt 0.0333] [--attrs a,b,...]

Constant buffers are filled the way the game fills them for a still owner at the origin (identity transforms), with the
game's buffer layouts (global 32, system 48, owner 512, emitter 32); the emitter-bound parameters of the external
buffer (spawn interval, interpolated start, spawn group, execution count) are set for one burst of N."""
import argparse, struct, sys
import numpy as np
sys.path[:0] = ['/work/nconv/tools', '/work/fx1018/editor/Python', '/work/cs',
                '/work/iostore']
import nio, nvmrun
from gv import LAYOUTS
from zen import Zen
from iostore import oodle
import scriptobjs

IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def g(v, *keys):
    for k in keys:
        if v is None:
            return None
        if v.kind == 'struct':
            v = v.value.get(k)
        elif v.kind == 'native':
            v = v.value.get(k) if isinstance(v.value, dict) else None
        else:
            return None
    return v


def num(v, default=0):
    return default if v is None or v.zero else v.value


def arr_bytes(v):
    return b'' if v is None or v.zero else bytes(int(x.value) for x in v.value)


def buffers(dt=1 / 30, age=0.0, num_particles=0, spawn_scale=1.0, layout=(32, 48, 512, 32)):
    G = struct.pack('<5fi2i', dt, dt, 1 / dt, age, age, 3, 0, 0)
    S = struct.pack('<4f5i3i', 0.0, 300.0, 0.0, age, 0, 1, 1, 1, 0, 1234, 0, 0)
    O = struct.pack('<96f', *(IDENT * 6)) + struct.pack('<4f', 0, 0, 0, 1) + struct.pack('<4f', 0, 0, 0, 0) * 2 + \
        struct.pack('<4f', 1, 0, 0, 0) + struct.pack('<4f', 0, 1, 0, 0) + struct.pack('<4f', 0, 0, 1, 0) + \
        struct.pack('<4f', 1, 1, 1, 0)
    O += b'\0' * (layout[2] - len(O))
    E = struct.pack('<2i2f2i2i', num_particles, 0, spawn_scale, age, 77, 99, 0, 0)
    assert (len(G), len(S), len(O), len(E)) == tuple(layout), (len(G), len(S), len(O), len(E))
    return G, S, O, E


class Script:
    def __init__(self, z, idx, sp):
        cls, v, extra, data = nio.read_export(z, idx, sp)
        assert cls == 'NiagaraScript'
        self.usage = str(g(v, 'Usage').value)
        vm = g(v, 'CachedScriptVM')
        code = arr_bytes(g(vm, 'ByteCode'))
        us = num(g(vm, 'UncompressedSize'), 0)
        self.code = oodle(code, us) if us > 0 else code
        self.ntemp = num(g(vm, 'NumTempRegisters'))
        self.literals = arr_bytes(g(vm, 'ScriptLiterals'))
        self.ext = []
        self.fn_names = []
        for fn in (g(vm, 'CalledVMExternalFunctions').value if g(vm, 'CalledVMExternalFunctions') is not None and not g(vm, 'CalledVMExternalFunctions').zero else []):
            ipl = g(fn, 'InputParamLocations')
            self.ext.append((0 if ipl is None or ipl.zero else len(ipl.value), num(g(fn, 'NumOutputs'))))
            self.fn_names.append((str(g(fn, 'Name').value), str(g(fn, 'OwnerName').value)))
        dii = g(vm, 'DataInterfaceInfo')
        self.di_names = [str(g(x, 'Name').value) for x in (dii.value if dii is not None and not dii.zero else [])]
        cdi = g(v, 'CachedDefaultDataInterfaces')
        self.di_images = []
        for x in (cdi.value if cdi is not None and not cdi.zero else []):
            im = x.value.get('image')
            self.di_images.append((im['image'], im) if im else (None, None))
        st = g(v, 'ScriptExecutionParamStore')
        self.psize = num(g(st, 'ParameterSize'))
        self.pdata = bytearray(arr_bytes(g(st, 'ParameterData')))
        self.params = {}
        so = g(st, 'SortedParameterOffsets')
        for x in (so.value if so is not None and not so.zero else []):
            self.params[str(x.value['Name'])] = (x.value['Offset'], x.value['td']['vfx1']['hash'] if x.value['td'].get('vfx1') else None,
                                                 x.value['td']['vfx1']['utype'] if x.value['td'].get('vfx1') else None)
        self.interpolated = self.usage == 'ParticleSpawnScriptInterpolated'

    def set_param(self, name, fmt, *values):
        for nm in (name, 'PREV_' + name):
            p = self.params.get(nm)
            if p is None or p[2] == 1:
                continue
            struct.pack_into(fmt, self.pdata, p[0], *values)

    def functions(self):
        out = []
        for (fname, owner) in self.fn_names:
            if owner not in self.di_names:
                raise nvmrun.VMError('function %s owner %s not among the data interfaces %s' % (fname, owner, self.di_names))
            k = self.di_names.index(owner)
            img = self.di_images[k][0]
            comps = nvmrun.CURVE_FUNCTIONS.get(fname)
            if img is None or comps is None:
                raise nvmrun.VMError('function %s of %s not simulated' % (fname, owner))
            out.append(nvmrun.curve_sampler(img, comps))
        return out

    def constants(self, G, S, O, E):
        ext = bytes(self.pdata[:self.psize])
        tables = G + S + O + E + ext
        if self.interpolated:
            prev = bytes(self.pdata[self.psize:2 * self.psize])
            tables += G + S + O + E + prev
        return tables + self.literals


def layout(variables):
    """{name: ('f'|'i', [component indices])} in dataset order, and the float/int component counts"""
    nf = ni = 0
    out = {}
    for nm, th in variables:
        fl, il, sz = LAYOUTS[th]
        if fl:
            out[nm] = ('f', list(range(nf, nf + len(fl)))); nf += len(fl)
        if il:
            out[nm if not fl else nm + '#int'] = ('i', list(range(ni, ni + len(il)))); ni += len(il)
    return out, nf, ni


def emitter_info(z, sp, emitter_index):
    """(unique name, spawn script export, update script export, particle dataset variables) of an emitter"""
    cls, v, extra, data = nio.read_export(z, emitter_index, sp)
    name = str(g(v, 'UniqueEmitterName').value)
    spawn = num(g(v, 'SpawnScriptProps', 'Script')) - 1
    update = num(g(v, 'UpdateScriptProps', 'Script')) - 1
    sys_i = [i for i in range(len(z.exports)) if nio.read_export(z, i, sp)[0] == 'NiagaraSystem'][0]
    cls, sv, sextra, sdata = nio.read_export(z, sys_i, sp)
    handles = [num(g(h, 'Instance')) - 1 for h in g(sv, 'EmitterHandles').value]
    k = handles.index(emitter_index)
    tail = sextra['tail']
    u = nio.usmap()
    r = nio.Reader(u, z.names, tail, 8, len(tail))
    for j in range(struct.unpack_from('<i', tail, 4)[0]):
        st = r.props('NiagaraEmitterCompiledData')
        if j == k:
            ds = st.value['DataSetCompiledData'].value
            variables = [(str(x.value['Name']), x.value['td']['vfx1']['hash']) for x in ds['Variables'].value]
            return name, spawn, update, variables
    raise ValueError('no compiled data for emitter %d' % emitter_index)


def simulate(path, emitter_index, n=8, frames=3, dt=1 / 30, attrs=None, quiet=False):
    sp, _ = scriptobjs.load()
    z = Zen(open(path, 'rb').read())
    name, si, ui, variables = emitter_info(z, sp, emitter_index)
    lay, nf, ni = layout(variables)
    spawn = Script(z, si, sp)
    update = Script(z, ui, sp)
    for s in (spawn, update):
        s.set_param('Engine.ExecutionCount', '<i', n)
        s.set_param(name + '.SpawnInterval', '<f', 0.0)
        s.set_param(name + '.InterpSpawnStartDt', '<f', 0.0)
        s.set_param(name + '.SpawnGroup', '<i', 0)
        s.set_param(name + '.SpawnRate', '<f', 0.0)
    rng = np.random.default_rng(7)
    G, S, O, E = buffers(dt=dt, num_particles=0)
    vm = nvmrun.VM(spawn.code, spawn.ext, spawn.ntemp)
    res = vm(n, spawn.constants(G, S, O, E), outputs={0: (nf, ni)}, functions=spawn.functions(), rng=rng)[0]
    history = [('spawn', res)]
    missing = [nm for nm, (k, cs) in lay.items() if not all(c in res['written_' + k] for c in cs)]
    if missing and not quiet:
        print('  spawn script never writes:', missing)
    cur = res
    vmu = nvmrun.VM(update.code, update.ext, update.ntemp)
    for fr in range(frames):
        count = cur['count']
        if count <= 0:
            break
        G, S, O, E = buffers(dt=dt, age=(fr + 1) * dt, num_particles=count)
        inp = {0: {'f': cur['f'][:, :count], 'i': cur['i'][:, :count]}}
        cur = vmu(count, update.constants(G, S, O, E), inputs=inp, outputs={0: (nf, ni)},
                  functions=update.functions(), rng=rng)[0]
        history.append(('update %d' % (fr + 1), cur))
    if not quiet:
        for label, r in history:
            print('== %s %s: %d particles' % (name, label, r['count']))
            for nm, (k, cols) in lay.items():
                if attrs and not any(a in nm for a in attrs):
                    continue
                vals = r[k][cols, :max(r['count'], 0)]
                if vals.size == 0:
                    continue
                show = ' '.join('[%s]' % ','.join('%.4g' % x for x in vals[:, j]) for j in range(min(4, vals.shape[1])))
                print('   %-60s %s' % (nm[:60], show))
    return history, lay


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('package')
    ap.add_argument('emitter', type=int)
    ap.add_argument('--spawn', type=int, default=6)
    ap.add_argument('--frames', type=int, default=2)
    ap.add_argument('--dt', type=float, default=1 / 30)
    ap.add_argument('--attrs', default='')
    a = ap.parse_args()
    simulate(a.package, a.emitter, a.spawn, a.frames, a.dt, [x for x in a.attrs.split(',') if x])
