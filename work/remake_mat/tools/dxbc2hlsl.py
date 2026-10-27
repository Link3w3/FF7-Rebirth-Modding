"""D3D11 shader assembly (Microsoft's disassembler, hex literals: D3DDisassemble flag 0x80) -> HLSL that does the same
thing, instruction by instruction.

Registers are kept as uint4 (their bits): float instructions read them through asfloat and store through asuint,
integer ones work on them directly. (Kept as float4, small integers are float denormals, which Microsoft's compiler
folds to 0.)

Two uses:
  * the check: the lifted body inside a wrapper with the original's signature, cbuffers and resource registers, compiled
    again with Microsoft's compiler, must behave exactly like the original (lift_check.py runs both on the same inputs);
  * the rebuilt Remake masters: the same body inside a material Custom node, its inputs (v#), cbuffers (cb#) and textures
    (t#, s#) supplied by the node (an Env decides how each is spelled).

    dxbc2hlsl.py <shader.asm>            prints the wrapper (the check's shader)"""
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxbc2cpp import Op, Gen, split_ops

COMP = 'xyzw'


class Env:
    """How the lifted body names what the shader reads (each a uint4 of bits). The default: the original's registers,
    as the check's wrapper declares them."""

    def v(self, reg):
        return 'v%d' % reg

    def cb(self, buf, index):
        return 'cb%d[%s]' % (buf, index)

    def tex(self, reg):
        return 't%d' % reg

    def samp(self, sreg, treg):
        return 's%d' % sreg

    def load3d(self, treg, arg):
        """a texture3d load (the base pass's blue noise): None = the texture itself"""
        return None


class Lifter(Gen):
    def __init__(self, asm, env=None):
        self.env = env or Env()
        self.inputs = []      # (reg, mask, interpolation, sysval)
        self.input_sig = []   # from the comment header: (semantic, index, mask, register, sysvalue, format, used)
        self.output_sig = []
        self.cbs = {}         # buf -> size
        self.samplers = set()
        self.uses_coverage = False
        self.discards = False
        self.uses_bitfield = False
        self.cb_reads = set()  # (buf, static index) read
        self.dyn_cb = set()    # buffers read with a register index
        self.tex_reads = {}    # t# -> set of s# (or None for loads)
        super().__init__(asm, 'main')
        self._sig(asm)
        self.tmpn = 0

    # ---- what the shader declares
    def _sig(self, asm):
        txt = asm.replace('\x00', '')
        part = txt.split('// Output signature')
        # (the used mask can have gaps: "xy w")
        rx = re.compile(r'^// (\w+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\w+)[ \t]*([xyzw ]*?)\s*$', re.M)
        self.input_sig = [m.groups()[:6] + (m.group(7).replace(' ', ''),) for m in rx.finditer(part[0])]
        if len(part) > 1:
            head = re.split(r'^(?:ps|vs|gs|hs|ds|cs)_\d_\d', part[1], flags=re.M)[0]
            self.output_sig = [m.groups()[:6] + (m.group(7).replace(' ', ''),) for m in rx.finditer(head)]
        for raw in txt.splitlines():
            s = raw.split('//')[0].strip()
            m = re.match(r'dcl_constantbuffer CB(\d+)\[(\d+)\]', s)
            if m:
                self.cbs[int(m.group(1))] = int(m.group(2))
            m = re.match(r'dcl_sampler s(\d+)', s)
            if m:
                self.samplers.add(int(m.group(1)))
            m = re.match(r'dcl_input_ps(_siv|_sgv)?\s+(.*?)\s*v(\d+)(?:\.([xyzw]+))?(?:,\s*(\w+))?$', s)
            if m:
                self.inputs.append((int(m.group(3)), m.group(4) or 'xyzw', m.group(2).strip(), m.group(5)))
            if s.startswith('dcl_input vCoverage'):
                self.uses_coverage = True

    # ---- operands (all as uint expressions)
    def reg(self, o):
        if o.kind == 'r':
            return 'r%d' % o.reg
        if o.kind == 'v':
            return self.env.v(o.reg)
        if o.kind == 'o':
            return 'o%d' % o.reg
        if o.kind == 'x':
            return 'x%d[%s]' % (o.reg, self.hidx(o))
        raise ValueError(o.text)

    def hidx(self, o):
        st, rk, rr, rc = o.index
        if rk is None:
            return '%d' % st
        if rk == 'r':
            return '(int(r%d.%s) + %d)' % (rr, COMP[rc], st)
        if rk == 'v':
            return '(int(%s.%s) + %d)' % (self.env.v(rr), COMP[rc], st)
        raise ValueError('index %r' % (o.index,))

    def comp(self, o, c):
        return o.swz[c] if len(o.swz) > 1 else o.swz[0]

    def raw(self, o, k):
        """the source register's lane k: its bits"""
        if o.kind == 'l':
            return '0x%08xu' % o.lits[k]
        if o.kind == 'cb':
            if o.index[1] is None:
                self.cb_reads.add((o.reg, o.index[0]))
            else:
                self.dyn_cb.add(o.reg)
            return '%s.%s' % (self.env.cb(o.reg, self.hidx(o)), COMP[k])
        if o.kind == 'icb':
            return 'icb[%s].%s' % (self.hidx(o), COMP[k])
        if o.kind == 'vCoverage':
            self.uses_coverage = True
            return 'vCoverage'
        if o.kind in ('vPrim', 'vPrimitiveID'):
            return '0u'
        if o.kind == 'o':
            return 'asuint(o%d.%s)' % (o.reg, COMP[k])
        return '%s.%s' % (self.reg(o), COMP[k])

    def f(self, o, c):
        return self._f(o, self.comp(o, c))

    def fpos(self, o, i):
        return self._f(o, o.swz[i] if len(o.swz) > 1 else o.swz[0])

    def _f(self, o, k):
        if o.kind == 'l':
            e = 'asfloat(0x%08xu)' % o.lits[k]
        else:
            e = 'asfloat(%s)' % self.raw(o, k)
        if o.abs:
            e = 'abs(%s)' % e
        if o.neg:
            e = '(-%s)' % e
        return e

    def u(self, o, c):
        return self._u(o, self.comp(o, c))

    def upos(self, o, i):
        return self._u(o, o.swz[i] if len(o.swz) > 1 else o.swz[0])

    def _u(self, o, k):
        e = self.raw(o, k)
        if o.abs:
            e = 'asuint(abs(asint(%s)))' % e
        if o.neg:
            e = '(0u - %s)' % e
        return e

    def lane(self, o, c):
        """a raw copy (mov, movc); with modifiers, the float result"""
        if o.abs or o.neg:
            return 'asuint(%s)' % self.f(o, c)
        return self.raw(o, self.comp(o, c))

    # ---- writes: every component worked out first, then stored (a source may be the destination)
    def write(self, o, exprs, sat=False, kind='f'):
        """exprs per destination component: kind 'f' float expressions, 'u' uint expressions (bits)"""
        if o.kind == 'null':
            return
        vals = []
        for e in exprs:
            if kind == 'f':
                vals.append('asuint(%s)' % ('saturate(%s)' % e if sat else e))
            else:
                vals.append('asuint(saturate(asfloat(%s)))' % e if sat else e)
        if o.kind in ('oDepth', 'oDepthGE', 'oDepthLE'):
            self.emit('oDepth = asfloat(%s);' % vals[0])
            return
        comps = o.mask()
        if o.kind == 'o':
            ref = 'o%d' % o.reg
            if len(comps) == 1:
                self.emit('%s.%s = asfloat(%s);' % (ref, COMP[comps[0]], vals[0]))
            else:
                self.emit('{ ' + ' '.join('uint q%d = %s;' % (j, v) for j, v in enumerate(vals)) + ' '
                          + ' '.join('%s.%s = asfloat(q%d);' % (ref, COMP[c], j) for j, c in enumerate(comps)) + ' }')
            return
        ref = self.reg(o)
        if len(comps) == 1:
            self.emit('%s.%s = %s;' % (ref, COMP[comps[0]], vals[0]))
            return
        self.emit('{ ' + ' '.join('uint q%d = %s;' % (j, v) for j, v in enumerate(vals)) + ' '
                  + ' '.join('%s.%s = q%d;' % (ref, COMP[c], j) for j, c in enumerate(comps)) + ' }')

    # ---- the body
    def body_lines(self):
        self.out = []
        self.depth = 1
        for line in self.body:
            self.instr(line)
        return self.out

    def decls(self):
        d = ['uint4 r%d = uint4(0u, 0u, 0u, 0u);' % i for i in range(max(1, self.ntemps))]
        for x, n in sorted(self.xdecl.items()):
            d.append('uint4 x%d[%d];' % (x, n))
            d.append('[unroll] for (int xi%d = 0; xi%d < %d; ++xi%d) x%d[xi%d] = uint4(0u, 0u, 0u, 0u);' % (x, x, n, x, x, x))
        if self.icb:
            rows = ', '.join('uint4(%s)' % ', '.join('0x%08xu' % v for v in row) for row in self.icb)
            d.append('const uint4 icb[%d] = {%s};' % (len(self.icb), rows))
        return d

    def instr(self, line):
        m = re.match(r'^(\S+)\s*(.*)$', line)
        opc, rest = m.group(1), m.group(2)
        sat = False
        base = opc
        mres = re.match(r'^([a-z0-9_]+?)(_indexable)?(\([^)]*\))?(\([^)]*\))?$', opc)
        if mres:
            base = mres.group(1)
        if base.endswith('_sat'):
            sat = True
            base = base[:-4]
        aoff = None
        ma = re.match(r'^(\w+?)_aoffimmi\(([-\d]+),([-\d]+),([-\d]+)\)', opc)
        if ma:
            base = ma.group(1)
            aoff = (int(ma.group(2)), int(ma.group(3)), int(ma.group(4)))
        ops = [Op(x) for x in split_ops(rest)] if rest else []
        self.emit('// ' + line)
        if base in ('if_nz', 'if_z'):
            self.emit('[branch] if (%s %s 0u) {' % (self.u(ops[0], 0), '!=' if base == 'if_nz' else '=='))
            self.depth += 1
            return
        if base == 'else':
            self.depth -= 1
            self.emit('} else {')
            self.depth += 1
            return
        if base in ('endif', 'endloop', 'endswitch'):
            self.depth -= 1
            self.emit('}')
            return
        if base == 'loop':
            self.emit('[loop] for (;;) {')
            self.depth += 1
            return
        if base == 'break':
            self.emit('break;')
            return
        if base in ('breakc_nz', 'breakc_z'):
            self.emit('if (%s %s 0u) break;' % (self.u(ops[0], 0), '!=' if base == 'breakc_nz' else '=='))
            return
        if base == 'continue':
            self.emit('continue;')
            return
        if base in ('continuec_nz', 'continuec_z'):
            self.emit('if (%s %s 0u) continue;' % (self.u(ops[0], 0), '!=' if base == 'continuec_nz' else '=='))
            return
        if base == 'ret':
            self.emit('return;')
            return
        if base in ('retc_nz', 'retc_z'):
            self.emit('if (%s %s 0u) return;' % (self.u(ops[0], 0), '!=' if base == 'retc_nz' else '=='))
            return
        if base in ('discard_nz', 'discard_z'):
            self.discards = True
            self.emit('if (%s %s 0u) discard;' % (self.u(ops[0], 0), '!=' if base == 'discard_nz' else '=='))
            return
        if base == 'switch':
            self.emit('switch (int(%s)) {' % self.u(ops[0], 0))
            self.depth += 1
            return
        if base == 'case':
            self.emit('case %d:' % (Op(rest).lits[0] if rest.startswith('l(') else int(rest, 0)))
            return
        if base == 'default':
            self.emit('default:')
            return
        if base in ('nop',):
            return
        d = ops[0] if ops else None
        comps = d.mask() if d is not None and d.kind != 'null' else []
        n = len(comps)
        if base == 'mov':
            if sat:
                self.write(d, [self.f(ops[1], c) for c in comps], sat)
            else:
                self.write(d, [self.lane(ops[1], c) for c in comps], kind='u')
            return
        if base == 'movc':
            ex = ['((%s != 0u) ? %s : %s)' % (self.u(ops[1], c), self.lane(ops[2], c), self.lane(ops[3], c)) for c in comps]
            self.write(d, ex, sat, kind='u')
            return
        if base == 'swapc':
            d1 = ops[1]
            v0 = ['((%s != 0u) ? %s : %s)' % (self.u(ops[2], c), self.lane(ops[4], c), self.lane(ops[3], c)) for c in d.mask()] if d.kind != 'null' else []
            v1 = ['((%s != 0u) ? %s : %s)' % (self.u(ops[2], c), self.lane(ops[3], c), self.lane(ops[4], c)) for c in d1.mask()] if d1.kind != 'null' else []
            self.emit('{')
            self.depth += 1
            if v0:
                self.emit(' '.join('uint sa%d = %s;' % (j, v) for j, v in enumerate(v0)))
            if v1:
                self.emit(' '.join('uint sb%d = %s;' % (j, v) for j, v in enumerate(v1)))
            if v0:
                self.write(d, ['sa%d' % j for j in range(len(v0))], kind='u')
            if v1:
                self.write(d1, ['sb%d' % j for j in range(len(v1))], kind='u')
            self.depth -= 1
            self.emit('}')
            return
        F1 = {'sqrt': 'sqrt(%s)', 'rsq': 'rsqrt(%s)', 'rcp': 'rcp(%s)', 'exp': 'exp2(%s)', 'log': 'log2(%s)', 'frc': 'frac(%s)',
              'round_ne': 'round(%s)', 'round_ni': 'floor(%s)', 'round_pi': 'ceil(%s)', 'round_z': 'trunc(%s)',
              'deriv_rtx': 'ddx(%s)', 'deriv_rtx_coarse': 'ddx_coarse(%s)', 'deriv_rtx_fine': 'ddx_fine(%s)',
              'deriv_rty': 'ddy(%s)', 'deriv_rty_coarse': 'ddy_coarse(%s)', 'deriv_rty_fine': 'ddy_fine(%s)'}
        if base in F1:
            self.write(d, [F1[base] % self.f(ops[1], c) for c in comps], sat)
            return
        F2 = {'add': '(%s + %s)', 'mul': '(%s * %s)', 'div': '(%s / %s)', 'min': 'min(%s, %s)', 'max': 'max(%s, %s)'}
        if base in F2:
            self.write(d, [F2[base] % (self.f(ops[1], c), self.f(ops[2], c)) for c in comps], sat)
            return
        if base == 'mad':
            self.write(d, ['mad(%s, %s, %s)' % (self.f(ops[1], c), self.f(ops[2], c), self.f(ops[3], c)) for c in comps], sat)
            return
        FC = {'lt': '<', 'ge': '>=', 'eq': '==', 'ne': '!='}
        if base in FC:
            self.write(d, ['((%s %s %s) ? 0xffffffffu : 0u)' % (self.f(ops[1], c), FC[base], self.f(ops[2], c)) for c in comps], kind='u')
            return
        if base in ('dp2', 'dp3', 'dp4'):
            k = int(base[2])
            a = 'float%d(%s)' % (k, ', '.join(self.fpos(ops[1], i) for i in range(k)))
            b = 'float%d(%s)' % (k, ', '.join(self.fpos(ops[2], i) for i in range(k)))
            self.write(d, ['dot(%s, %s)' % (a, b)] * n, sat)
            return
        if base == 'sincos':
            ds, dc = ops[0], ops[1]
            if ds.kind != 'null':
                self.write(ds, ['sin(%s)' % self.f(ops[2], c) for c in ds.mask()], sat)
            if dc.kind != 'null':
                self.write(dc, ['cos(%s)' % self.f(ops[2], c) for c in dc.mask()], sat)
            return
        I2 = {'iadd': '({a} + {b})', 'and': '({a} & {b})', 'or': '({a} | {b})', 'xor': '({a} ^ {b})',
              'ishl': '({a} << ({b} & 31u))', 'ishr': 'uint(int({a}) >> int({b} & 31u))', 'ushr': '({a} >> ({b} & 31u))',
              'imin': 'uint(min(int({a}), int({b})))', 'imax': 'uint(max(int({a}), int({b})))',
              'umin': 'min({a}, {b})', 'umax': 'max({a}, {b})',
              'ieq': '(({a} == {b}) ? 0xffffffffu : 0u)', 'ine': '(({a} != {b}) ? 0xffffffffu : 0u)',
              'ilt': '((int({a}) < int({b})) ? 0xffffffffu : 0u)', 'ige': '((int({a}) >= int({b})) ? 0xffffffffu : 0u)',
              'ult': '(({a} < {b}) ? 0xffffffffu : 0u)', 'uge': '(({a} >= {b}) ? 0xffffffffu : 0u)'}
        if base in I2:
            self.write(d, [I2[base].format(a=self.u(ops[1], c), b=self.u(ops[2], c)) for c in comps], kind='u')
            return
        I1 = {'not': '(~{a})', 'ineg': '(0u - {a})', 'countbits': 'countbits({a})', 'bfrev': 'reversebits({a})',
              'firstbit_hi': 'firstbithigh({a})', 'firstbit_lo': 'firstbitlow({a})', 'firstbit_shi': 'uint(firstbithigh(int({a})))'}
        if base in I1:
            self.write(d, [I1[base].format(a=self.u(ops[1], c)) for c in comps], kind='u')
            return
        if base in ('imad', 'umad'):
            self.write(d, ['(%s * %s + %s)' % (self.u(ops[1], c), self.u(ops[2], c), self.u(ops[3], c)) for c in comps], kind='u')
            return
        if base in ('ubfe', 'ibfe', 'bfi'):
            self.uses_bitfield = True
            if base == 'ubfe':
                ex = ['EMS_ubfe(%s, %s, %s)' % (self.u(ops[1], c), self.u(ops[2], c), self.u(ops[3], c)) for c in comps]
            elif base == 'ibfe':
                ex = ['EMS_ibfe(%s, %s, %s)' % (self.u(ops[1], c), self.u(ops[2], c), self.u(ops[3], c)) for c in comps]
            else:
                ex = ['EMS_bfi(%s, %s, %s, %s)' % (self.u(ops[1], c), self.u(ops[2], c), self.u(ops[3], c), self.u(ops[4], c)) for c in comps]
            self.write(d, ex, kind='u')
            return
        if base == 'ftoi':
            self.write(d, ['uint(int(%s))' % self.f(ops[1], c) for c in comps], kind='u')
            return
        if base == 'ftou':
            self.write(d, ['uint(%s)' % self.f(ops[1], c) for c in comps], kind='u')
            return
        if base == 'f32tof16':
            self.write(d, ['f32tof16(%s)' % self.f(ops[1], c) for c in comps], kind='u')
            return
        if base == 'itof':
            self.write(d, ['float(int(%s))' % self.u(ops[1], c) for c in comps], sat)
            return
        if base == 'utof':
            self.write(d, ['float(%s)' % self.u(ops[1], c) for c in comps], sat)
            return
        if base == 'f16tof32':
            self.write(d, ['f16tof32(%s)' % self.u(ops[1], c) for c in comps], sat)
            return
        if base in ('imul', 'umul'):
            hi, lo = ops[0], ops[1]
            if hi.kind != 'null':
                raise NotImplementedError('imul/umul high half')
            if lo.kind != 'null':
                self.write(lo, ['(%s * %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in lo.mask()], kind='u')
            return
        if base == 'udiv':
            q, rm = ops[0], ops[1]
            if q.kind != 'null':
                self.write(q, ['(%s / %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in q.mask()], kind='u')
            if rm.kind != 'null':
                self.write(rm, ['(%s %% %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in rm.mask()], kind='u')
            return
        if base in ('sample', 'sample_l', 'sample_b', 'sample_d', 'sample_c', 'sample_c_lz', 'gather4', 'gather4_c'):
            self.hsample(base, ops, sat, aoff)
            return
        if base in ('ld', 'ld_ms'):
            self.hload(ops, sat)
            return
        if base == 'resinfo':
            self.hresinfo(opc, ops)
            return
        raise NotImplementedError(line)

    def coordv(self, o, n):
        return 'float%d(%s)' % (n, ', '.join(self.fpos(o, i) for i in range(n))) if n > 1 else self.fpos(o, 0)

    def hsample(self, base, ops, sat, aoff):
        d, co, t, s = ops[0], ops[1], ops[2], ops[3]
        ty = self.res.get(t.reg, 'texture2d')
        n = {'texture2d': 2, 'texture3d': 3, 'texturecube': 3, 'texture2darray': 3}.get(ty, 2)
        uv = self.coordv(co, n)
        tex = self.env.tex(t.reg)
        smp = self.env.samp(s.reg, t.reg)
        self.tex_reads.setdefault(t.reg, set()).add(s.reg)
        off = ''
        if aoff:
            off = ', int%d(%s)' % (2 if n == 2 else 3, ', '.join(str(x) for x in aoff[:2 if n == 2 else 3]))
        g = 2 if ty in ('texture2d', 'texture2darray') else 3
        if base == 'sample':
            call = '%s.Sample(%s, %s%s)' % (tex, smp, uv, off)
        elif base == 'sample_l':
            call = '%s.SampleLevel(%s, %s, %s%s)' % (tex, smp, uv, self.fpos(ops[4], 0), off)
        elif base == 'sample_b':
            call = '%s.SampleBias(%s, %s, %s%s)' % (tex, smp, uv, self.fpos(ops[4], 0), off)
        elif base == 'sample_d':
            call = '%s.SampleGrad(%s, %s, %s, %s%s)' % (tex, smp, uv, self.coordv(ops[4], g), self.coordv(ops[5], g), off)
        elif base == 'sample_c':
            call = '%s.SampleCmp(%s, %s, %s%s).xxxx' % (tex, smp, uv, self.fpos(ops[4], 0), off)
        elif base == 'sample_c_lz':
            call = '%s.SampleCmpLevelZero(%s, %s, %s%s).xxxx' % (tex, smp, uv, self.fpos(ops[4], 0), off)
        elif base == 'gather4':
            call = '%s.Gather(%s, %s%s)' % (tex, smp, uv, off)
        else:
            call = '%s.GatherCmp(%s, %s, %s%s)' % (tex, smp, uv, self.fpos(ops[4], 0), off)
        self.tmpn += 1
        tn = 'tr%d' % self.tmpn
        self.emit('float4 %s = %s;' % (tn, call))
        sw = t.swz if t.swz else [0, 1, 2, 3]
        self.write(d, ['%s.%s' % (tn, COMP[sw[c] if len(sw) > 1 else sw[0]]) for c in d.mask()], sat)

    def hload(self, ops, sat):
        d, co, t = ops[0], ops[1], ops[2]
        ty = self.res.get(t.reg, 'texture2d')
        tex = self.env.tex(t.reg)
        self.tex_reads.setdefault(t.reg, set()).add(None)
        if ty == 'texture3d':
            arg = 'int4(%s)' % ', '.join('int(%s)' % self.upos(co, i) for i in range(4))
        elif ty == 'buffer':
            arg = 'int(%s)' % self.upos(co, 0)
        else:
            arg = 'int3(int(%s), int(%s), int(%s))' % (self.upos(co, 0), self.upos(co, 1), self.upos(co, 3))
        call = self.env.load3d(t.reg, arg) if ty == 'texture3d' else None
        if call is None:
            call = '%s.Load(%s)' % (tex, arg)
        self.tmpn += 1
        tn = 'tr%d' % self.tmpn
        self.emit('float4 %s = %s;' % (tn, call))
        sw = t.swz if t.swz else [0, 1, 2, 3]
        self.write(d, ['%s.%s' % (tn, COMP[sw[c] if len(sw) > 1 else sw[0]]) for c in d.mask()], sat)

    def hresinfo(self, opc, ops):
        d, mip, t = ops[0], ops[1], ops[2]
        tex = self.env.tex(t.reg)
        self.tmpn += 1
        k = self.tmpn
        self.emit('uint w%d, h%d, l%d; %s.GetDimensions(%s, w%d, h%d, l%d);' % (k, k, k, tex, self.upos(mip, 0), k, k, k))
        sw = t.swz if t.swz else [0, 1, 2, 3]
        vals = ['w%d' % k, 'h%d' % k, '1u', 'l%d' % k]
        uint = '_uint' in opc
        ex = []
        for c in d.mask():
            v = vals[sw[c] if len(sw) > 1 else sw[0]]
            ex.append(v if uint else 'float(%s)' % v)
        self.write(d, ex, kind='u' if uint else 'f')


BITFIELD = """uint EMS_ubfe(uint w, uint o, uint v) { w &= 31u; o &= 31u; if (w == 0u) return 0u; if (w + o < 32u) return (v << (32u - w - o)) >> (32u - w); return v >> o; }
uint EMS_ibfe(uint w, uint o, uint v) { w &= 31u; o &= 31u; if (w == 0u) return 0u; if (w + o < 32u) return uint(int(v << (32u - w - o)) >> int(32u - w)); return uint(int(v) >> int(o)); }
uint EMS_bfi(uint w, uint o, uint ins, uint base) { w &= 31u; o &= 31u; uint m = (w == 0u) ? 0u : (((w == 32u) ? 0xffffffffu : ((1u << w) - 1u)) << o); return ((ins << o) & m) | (base & ~m); }
"""

TEXTYPES = {'texture2d': 'Texture2D<float4>', 'texture3d': 'Texture3D<float4>', 'texturecube': 'TextureCube<float4>',
            'texture2darray': 'Texture2DArray<float4>', 'buffer': 'Buffer<float4>'}


def wrapper(asm_text):
    """the check's shader: the lifted body with the original's signature, cbuffers, textures and samplers"""
    L = Lifter(asm_text)
    lines = L.body_lines()
    out = []
    if L.uses_bitfield:
        out.append(BITFIELD)
    for b, n in sorted(L.cbs.items()):
        out.append('cbuffer CB%d : register(b%d) { uint4 cb%d[%d]; };' % (b, b, b, n))
    for t, ty in sorted(L.res.items()):
        out.append('%s t%d : register(t%d);' % (TEXTYPES.get(ty, 'Texture2D<float4>'), t, t))
    for s in sorted(L.samplers):
        out.append('SamplerState s%d : register(s%d);' % (s, s))
    params = []
    decl = {x[0]: x for x in L.inputs}
    for r in L.input_sig:
        reg = int(r[3])
        sem, idx, sysv = r[0], r[1], r[4]
        interp = decl[reg][2] if reg in decl else ''
        q = interp
        q = q.replace('linear noperspective centroid', 'noperspective centroid').replace('linear noperspective', 'noperspective')
        q = q.replace('constant', 'nointerpolation').replace('linear centroid', 'centroid').replace('linear sample', 'sample')
        q = re.sub(r'^linear\b', '', q).strip()
        if sysv == 'POS':
            params.append(('%s float4 in_v%d : SV_Position' % (q, reg)).strip())
        elif sysv == 'FFACE':
            params.append('bool in_v%d : SV_IsFrontFace' % reg)
        elif r[5] == 'uint':
            params.append(('%s uint4 in_v%d : %s%s' % (q or 'nointerpolation', reg, sem, idx)).strip())
        elif r[5] == 'int':
            params.append(('%s int4 in_v%d : %s%s' % (q or 'nointerpolation', reg, sem, idx)).strip())
        else:
            params.append(('%s float4 in_v%d : %s%s' % (q, reg, sem, idx)).strip())
    if L.uses_coverage:
        params.append('uint vCoverage : SV_Coverage')
    for r in L.output_sig:
        params.append('out float4 o%s : SV_Target%s' % (r[3], r[1]))
    out.append('void main(%s)' % ',\n          '.join(params))
    out.append('{')
    for r in L.input_sig:
        reg = int(r[3])
        if r[4] == 'FFACE':
            out.append('    uint4 v%d = uint4(in_v%d ? 0xffffffffu : 0u, 0u, 0u, 0u);' % (reg, reg))
        else:
            out.append('    uint4 v%d = asuint(in_v%d);' % (reg, reg))
    for r in L.output_sig:
        out.append('    o%s = float4(0.0, 0.0, 0.0, 0.0);' % r[3])
    out.extend('    ' + d for d in L.decls())
    out.extend(lines)
    out.append('}')
    return '\n'.join(out)


if __name__ == '__main__':
    print(wrapper(open(sys.argv[1], encoding='latin-1').read()))
