"""SQEX per-particle material parameters for converted emitters, from a per-emitter recipe (the Remake port).

Like nindep, the game's particle materials read their tone, luminance and coordinates from Vector4 particle attributes
(FX_Gen_<Kind>_0_SetParticleMaterialParameter.IndependentParameter<k>, bound by the renderer's
VfxMaterialIndependentParameters<k>_Binding). Here each component of each parameter is a product of factors:

    ['const', v]                 a number
    ['color', c]                 Particles.Color component c (0..3) as the script writes it
    ['attr', name, c]            component c of another float attribute the script writes (DynamicMaterialParameter)

e.g. IndependentParameter1.w = Color.a * 6000:  [['color', 3], ['const', 6000.0]].

The attributes go into the particle data set (sorted in by name, case-insensitively, as the game's are) and the
scripts' data set 0 component operands are moved to the new layout. Every write of a source component is copied to a
new temporary register right after it (the script may reuse its register later); after the script's last data set 0
output, each parameter component is computed (mul) from those copies and written with the same index register.
"""
import struct
import nvvm

VEC4 = (0x61a8c652, 2)
COLOR = 0xe2a7510c
DEFAULTS = {'color': 1.0, 'attr': 0.0}       # a source the script never writes: white / zero


def float_components(vars_, layouts):
    out, at = {}, 0
    for nm, th in vars_:
        fl = layouts[th[0]][0]
        out[nm] = list(range(at, at + len(fl)))
        at += len(fl)
    return out, at


class Plan:
    """the new particle data set of one emitter, how its float components move, what the parameters are made of"""

    TEMPS = True          # transform takes and returns the script's temporary register count

    def __init__(self, vars_, layouts, prefix, spec):
        """vars_: [(name, (type hash, utype))] of the emitter's particle data set; prefix: the parameters' name up to the
        index ('FX_Gen_Mesh_0_SetParticleMaterialParameter.IndependentParameter'); spec: {k: [4 x [factor, ...]]}"""
        self.old_vars = list(vars_)
        self.prefix = prefix
        self.spec = {int(k): v for k, v in spec.items()}
        names = {nm for nm, th in vars_}
        added = [(prefix + str(k), VEC4) for k in sorted(self.spec)]
        for nm, th in added:
            if nm in names:
                raise ValueError('the emitter already has %s' % nm)
        self.new_vars = sorted(self.old_vars + added, key=lambda t: t[0].lower())
        old, self.old_total = float_components(self.old_vars, layouts)
        new, self.new_total = float_components(self.new_vars, layouts)
        self.remap = {}
        for nm, comps in old.items():
            for a, b in zip(comps, new[nm]):
                self.remap[a] = b
        self.params = {k: new[prefix + str(k)] for k in self.spec}
        self.old = old
        # the old component index of every source factor
        self.sources = {}
        for k, comps in self.spec.items():
            if len(comps) != 4:
                raise ValueError('parameter %d: 4 components wanted' % k)
            for factors in comps:
                for f in factors:
                    key = self._source_key(f)
                    if key is not None and key not in self.sources:
                        self.sources[key] = self._source_comp(key)
        self.warnings = []
        self.color = old.get('Color')   # (for the report)

    def _source_key(self, f):
        if f[0] == 'const':
            return None
        if f[0] == 'color':
            return ('Color', int(f[1]))
        if f[0] == 'attr':
            return (str(f[1]), int(f[2]))
        raise ValueError('unknown factor %r' % (f,))

    def _source_comp(self, key):
        nm, c = key
        comps = self.old.get(nm)
        if comps is None or c >= len(comps):
            return None                  # the emitter has no such attribute: its default
        return comps[c]

    def transform(self, code, ext_counts, literal_base, literals, num_temp):
        """-> (code, literals, num_temp)"""
        lits = bytearray(literals)
        const_at = {}

        def const(value):
            v = struct.unpack('<f', struct.pack('<f', float(value)))[0]
            if v not in const_at:
                const_at[v] = literal_base + len(lits)
                lits.extend(struct.pack('<f', v))
            return const_at[v]

        ins = nvvm.decode(code, ext_counts)
        # the source components this script writes, and where its last data set 0 output is
        comp_to_key = {c: k for k, c in self.sources.items() if c is not None}
        temps = {}                                  # source key -> its copy's register
        for x in ins:
            if x.op == 'outputdata_float' and x.operands[0][2] == 0 and x.operands[3][2] in comp_to_key:
                key = comp_to_key[x.operands[3][2]]
                if key not in temps:
                    temps[key] = num_temp + len(temps)
        work = num_temp + len(temps)
        last = max((i for i, x in enumerate(ins) if x.op == 'outputdata_float' and x.operands[0][2] == 0), default=None)
        if last is None:
            raise ValueError('the script writes no particle attribute')
        mul = nvvm.OP['mul']
        outp = nvvm.OP['outputdata_float']
        out = bytearray()
        for i, x in enumerate(ins):
            body = bytearray(code[x.at:x.at + x.size])
            extra = bytearray()
            if x.op in ('inputdata_float', 'inputdata_noadvance_float'):
                ds, comp = x.operands[0][2], x.operands[1][2]
                if ds == 0:
                    struct.pack_into('<H', body, x.operands[1][1] - x.at, self.remap[comp])
            elif x.op == 'outputdata_float':
                ds, ireg, (sk, spos, sv), comp = x.operands[0][2], x.operands[1][2], x.operands[2], x.operands[3][2]
                if ds == 0:
                    struct.pack_into('<H', body, x.operands[3][1] - x.at, self.remap[comp])
                    key = comp_to_key.get(comp)
                    if key is not None:
                        # t = src * 1 (a constant source: both operands constants)
                        extra += struct.pack('<BBHHH', mul, 3 if sk == 'c' else 2, sv, const(1.0), temps[key])
                    if i == last:
                        extra += self._emit(ireg, temps, work, const, mul, outp)
            out += body + extra
        back = nvvm.decode(bytes(out), ext_counts)
        assert back[-1].op == 'done'
        return bytes(out), bytes(lits), work + 1

    def _emit(self, ireg, temps, work, const, mul, outp):
        b = bytearray()
        for k in sorted(self.spec):
            for c, factors in enumerate(self.spec[k]):
                dest = self.params[k][c]
                k_const = 1.0
                regs = []
                for f in factors:
                    key = self._source_key(f)
                    if key is None:
                        k_const *= float(f[1])
                    elif key in temps:
                        regs.append(temps[key])
                    else:
                        d = DEFAULTS['color' if key[0] == 'Color' else 'attr']
                        if (key, d) not in self.warnings:
                            self.warnings.append((key, d))
                        k_const *= d
                if not regs:
                    b += struct.pack('<BBHHHH', outp, 1, 0, ireg, const(k_const), dest)
                    continue
                src = regs[0]
                for r in regs[1:]:
                    b += struct.pack('<BBHHH', mul, 0, src, r, work)
                    src = work
                if abs(k_const - 1.0) > 1e-12:
                    b += struct.pack('<BBHHH', mul, 2, src, const(k_const), work)
                    src = work
                b += struct.pack('<BBHHHH', outp, 0, 0, ireg, src, dest)
        return b
