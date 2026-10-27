"""D3D11 shader assembly (Microsoft's disassembler, hex literals: D3DDisassemble flag 0x80) -> C++ for the material
checker (dxbc_cpu.hpp). Every register lane keeps its exact bits and its float value with derivatives.
    dxbc2cpp.py <shader.asm> <function name> [out.cpp]"""
import re
import sys

COMP = 'xyzw'

FLOAT1 = {'sqrt': 'sqrt_', 'rsq': 'rsq_', 'rcp': 'rcp_', 'exp': 'exp_', 'log': 'log_', 'frc': 'frc_',
          'round_ne': 'round_ne_', 'round_ni': 'round_ni_', 'round_pi': 'round_pi_', 'round_z': 'round_z_',
          'deriv_rtx': 'dx_', 'deriv_rtx_coarse': 'dx_', 'deriv_rtx_fine': 'dx_',
          'deriv_rty': 'dy_', 'deriv_rty_coarse': 'dy_', 'deriv_rty_fine': 'dy_'}
FLOAT2 = {'add': 'add_', 'mul': 'mul_', 'div': 'div_', 'min': 'min_', 'max': 'max_'}
FCMP = {'lt': 'lt_', 'ge': 'ge_', 'eq': 'eq_', 'ne': 'ne_'}
INT2 = {'iadd': '({a} + {b})', 'and': '({a} & {b})', 'or': '({a} | {b})', 'xor': '({a} ^ {b})',
        'ishl': 'ishl_({a}, {b})', 'ishr': 'ishr_({a}, {b})', 'ushr': 'ushr_({a}, {b})',
        'imin': 'imin_({a}, {b})', 'imax': 'imax_({a}, {b})', 'umin': 'umin_({a}, {b})', 'umax': 'umax_({a}, {b})',
        'ieq': 'ieq_({a}, {b})', 'ine': 'ine_({a}, {b})', 'ilt': 'ilt_({a}, {b})', 'ige': 'ige_({a}, {b})',
        'ult': 'ult_({a}, {b})', 'uge': 'uge_({a}, {b})'}
INT1 = {'not': '(~{a})', 'ineg': '(0u - {a})', 'countbits': 'countbits_({a})', 'bfrev': 'bfrev_({a})',
        'firstbit_hi': 'firstbit_hi_({a})', 'firstbit_lo': 'firstbit_lo_({a})', 'firstbit_shi': 'firstbit_shi_({a})'}
INT3 = {'imad': '({a} * {b} + {c})', 'umad': '({a} * {b} + {c})', 'ubfe': 'ubfe_({a}, {b}, {c})', 'ibfe': 'ibfe_({a}, {b}, {c})'}
F2I = {'ftoi': 'ftoi_', 'ftou': 'ftou_', 'f32tof16': 'f32tof16_'}
I2F = {'itof': 'itof_', 'utof': 'utof_', 'f16tof32': 'f16tof32_'}


def split_ops(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class Op:
    def __init__(self, text):
        t = text.strip()
        self.text = t
        self.neg = self.abs = False
        if t.startswith('-'):
            self.neg = True
            t = t[1:].strip()
        if t.startswith('|') and t.endswith('|'):
            self.abs = True
            t = t[1:-1].strip()
        elif t.startswith('|'):
            # |r0.x|.y style does not occur; keep simple
            self.abs = True
            t = t.strip('|')
        self.kind = None
        self.reg = None
        self.index = None       # (static, rel_kind, rel_reg, rel_comp)
        self.swz = None
        self.lits = None
        m = re.match(r'^l\((.*)\)$', t)
        if m:
            vals = [v.strip() for v in m.group(1).split(',')]
            lits = [int(v, 16) if v.startswith('0x') or v.startswith('-0x') else self._lit(v) for v in vals]
            lits = [x & 0xffffffff for x in lits]
            if len(lits) == 1:
                lits = lits * 4
            while len(lits) < 4:
                lits.append(0)
            self.kind = 'l'
            self.lits = lits
            self.swz = [0, 1, 2, 3]
            return
        m = re.match(r'^(icb|cb\d+|x\d+)\[([^\]]*)\](?:\.([xyzw]+))?$', t)
        if m:
            base = m.group(1)
            if base.startswith('cb'):
                self.kind, self.reg = 'cb', int(base[2:])
            elif base == 'icb':
                self.kind = 'icb'
            else:
                self.kind, self.reg = 'x', int(base[1:])
            self.index = self._index(m.group(2))
            self.swz = self._swz(m.group(3))
            return
        m = re.match(r'^(r|v|o|t|s|u)(\d+)(?:\.([xyzw]+))?$', t)
        if m:
            self.kind, self.reg = m.group(1), int(m.group(2))
            self.swz = self._swz(m.group(3))
            return
        m = re.match(r'^(oDepth|oDepthGE|oDepthLE|oMask|vCoverage|vPrim|vOutputControlPointID|vPrimitiveID|vThreadID|vGSInstanceID)(?:\.([xyzw]+))?$', t)
        if m:
            self.kind = m.group(1)
            self.swz = self._swz(m.group(2))
            return
        if t == 'null':
            self.kind = 'null'
            return
        raise ValueError('operand: %r' % text)

    @staticmethod
    def _lit(v):
        import struct
        if '.' in v or 'e' in v.lower() or 'inf' in v.lower() or 'nan' in v.lower():
            return struct.unpack('<I', struct.pack('<f', float(v)))[0]
        return int(v)

    @staticmethod
    def _swz(s):
        if not s:
            return [0, 1, 2, 3]
        idx = [COMP.index(c) for c in s]
        return idx

    @staticmethod
    def _index(s):
        s = s.strip()
        m = re.match(r'^(r|x\d+\[[^\]]*\]|v)(\d*)\.([xyzw])\s*\+\s*(\d+)$', s)
        if m:
            return (int(m.group(4)), m.group(1), int(m.group(2)) if m.group(2) else 0, COMP.index(m.group(3)))
        m = re.match(r'^(r|v)(\d+)\.([xyzw])$', s)
        if m:
            return (0, m.group(1), int(m.group(2)), COMP.index(m.group(3)))
        return (int(s, 0), None, None, None)

    def mask(self):
        # a destination: the components written, in order
        return self.swz if self.swz is not None else [0, 1, 2, 3]


class Gen:
    def __init__(self, asm, name):
        self.name = name
        self.lines = []
        self.ntemps = 0
        self.xdecl = {}
        self.icb = []
        self.res = {}       # t# -> type
        self.out = []
        self.depth = 1
        self.parse(asm)

    def emit(self, s):
        self.out.append('    ' * self.depth + s)

    def parse(self, asm):
        body = []
        icb_lines = None
        for raw in asm.replace('\x00', '').splitlines():
            line = raw.split('//')[0].rstrip()
            if not line.strip():
                continue
            s = line.strip()
            if icb_lines is not None:
                icb_lines.append(s)
                # (the buffer's rows over several lines: it ends where its braces balance)
                j = ' '.join(icb_lines)
                if j.count('{') == j.count('}'):
                    self.icb = self._parse_icb(j)
                    icb_lines = None
                continue
            if s.startswith('dcl_immediateConstantBuffer'):
                icb_lines = [s]
                if s.count('{') and s.rstrip().endswith('}') and s.count('{') == s.count('}'):
                    self.icb = self._parse_icb(s)
                    icb_lines = None
                continue
            if s.startswith('dcl_temps'):
                self.ntemps = int(s.split()[1])
                continue
            if s.startswith('dcl_indexableTemp'):
                m = re.match(r'dcl_indexableTemp x(\d+)\[(\d+)\], (\d+)', s)
                self.xdecl[int(m.group(1))] = int(m.group(2))
                continue
            if s.startswith('dcl_resource'):
                m = re.match(r'dcl_resource_(\w+).*\bt(\d+)\b', s)
                if m:
                    self.res[int(m.group(2))] = m.group(1)
                continue
            if s.startswith('dcl_') or s.startswith(('ps_', 'vs_', 'gs_', 'hs_', 'ds_', 'cs_')):
                continue
            body.append(s)
        self.body = body

    @staticmethod
    def _parse_icb(s):
        vals = re.findall(r'\{([^{}]*)\}', s)
        rows = []
        for v in vals:
            parts = [p.strip() for p in v.split(',') if p.strip()]
            if not parts:
                continue
            row = []
            for p in parts:
                row.append(int(p, 16) & 0xffffffff if p.startswith(('0x', '-0x')) else Op._lit(p))
            while len(row) < 4:
                row.append(0)
            rows.append(row[:4])
        return rows

    # ---- operand expressions
    def regref(self, o):
        if o.kind == 'r':
            return 'r[%d]' % o.reg
        if o.kind == 'v':
            return 'io.v[%d]' % o.reg
        if o.kind == 'o':
            return 'io.o[%d]' % o.reg
        if o.kind == 'x':
            return 'x%d[%s]' % (o.reg, self.idx(o))
        raise ValueError(o.text)

    def idx(self, o):
        st, rk, rr, rc = o.index
        if rk is None:
            return '%d' % st
        if rk == 'r':
            return '((int)r[%d][%d].b + %d)' % (rr, rc, st)
        if rk == 'v':
            return '((int)io.v[%d][%d].b + %d)' % (rr, rc, st)
        raise ValueError('index %r' % (o.index,))

    def f(self, o, c):
        """float value of the source for destination component c"""
        k = o.swz[c] if len(o.swz) > 1 else o.swz[0]
        if o.kind == 'l':
            e = 'FB(0x%08xu)' % o.lits[k]
        elif o.kind == 'cb':
            e = 'cbF(io, %d, %s, %d)' % (o.reg, self.idx(o), k)
        elif o.kind == 'icb':
            e = 'FB(icbU(%s, %d))' % (self.idx(o), k)
        elif o.kind in ('vCoverage',):
            e = 'FB(io.coverage)'
        else:
            e = '%s[%d].f' % (self.regref(o), k)
        if o.abs:
            e = 'abs_(%s)' % e
        if o.neg:
            e = 'neg_(%s)' % e
        return e

    def u(self, o, c):
        """bits of the source for destination component c (integer instructions: '-' negates)"""
        k = o.swz[c] if len(o.swz) > 1 else o.swz[0]
        if o.kind == 'l':
            e = '0x%08xu' % o.lits[k]
        elif o.kind == 'cb':
            e = 'cbU(io, %d, %s, %d)' % (o.reg, self.idx(o), k)
        elif o.kind == 'icb':
            e = 'icbU(%s, %d)' % (self.idx(o), k)
        elif o.kind == 'vCoverage':
            e = 'io.coverage'
        elif o.kind == 'vPrim' or o.kind == 'vPrimitiveID':
            e = '0u'
        else:
            e = '%s[%d].b' % (self.regref(o), k)
        if o.abs:
            e = 'iabs_(%s)' % e
        if o.neg:
            e = '(0u - %s)' % e
        return e

    def lane(self, o, c):
        """the whole lane (raw copy), or a float result when the source has modifiers"""
        if o.abs or o.neg:
            return 'LF(%s)' % self.f(o, c)
        k = o.swz[c] if len(o.swz) > 1 else o.swz[0]
        if o.kind == 'l':
            return 'LB(0x%08xu)' % o.lits[k]
        if o.kind == 'cb':
            return 'cbL(io, %d, %s, %d)' % (o.reg, self.idx(o), k)
        if o.kind == 'icb':
            return 'LU(icbU(%s, %d))' % (self.idx(o), k)
        return '%s[%d]' % (self.regref(o), k)

    def dst(self, o):
        if o.kind == 'null':
            return None, []
        if o.kind in ('oDepth', 'oDepthGE', 'oDepthLE'):
            return 'io.oDepth', [0]
        if o.kind == 'oMask':
            return 'io.oMaskLane', [0]
        return self.regref(o), o.mask()

    def write(self, o, exprs, sat=False, kind='f'):
        """exprs: per destination component (in mask order). kind: 'f' float (D), 'u' bits, 'l' lane"""
        ref, comps = self.dst(o)
        if ref is None:
            return
        tmp = []
        for j, c in enumerate(comps):
            e = exprs[j]
            if kind == 'f':
                e = 'LF(%s)' % ('sat_(%s)' % e if sat else e)
            elif kind == 'u':
                e = 'LU(%s)' % e
            else:
                if sat:
                    e = 'LF(sat_((%s).f))' % e
            tmp.append(e)
        if ref == 'io.oDepth':
            self.emit('io.oDepth = %s;' % tmp[0])
            return
        if len(comps) == 1:
            self.emit('%s[%d] = %s;' % (ref, comps[0], tmp[0]))
            return
        self.emit('{ ' + ' '.join('const Lane t%d = %s;' % (j, e) for j, e in enumerate(tmp)) + ' '
                  + ' '.join('%s[%d] = t%d;' % (ref, c, j) for j, c in enumerate(comps)) + ' }')

    # ---- instructions
    def translate(self):
        hdr = ['void %s(DXIO& io)' % self.name, '{']
        hdr.append('    Lane r[%d][4];' % max(1, self.ntemps))
        for x, n in sorted(self.xdecl.items()):
            hdr.append('    Lane x%d[%d][4];' % (x, n))
        if self.icb:
            hdr.append('    static const uint32_t icb[%d][4] = {%s};' % (len(self.icb), ', '.join('{%s}' % ', '.join('0x%08xu' % v for v in row) for row in self.icb)))
            hdr.append('    auto icbU = [&](int i, int c) -> uint32_t { return (i >= 0 && i < %d) ? icb[i][c] : 0u; };' % len(self.icb))
        for line in self.body:
            self.instr(line)
        return '\n'.join(hdr + self.out + ['}'])

    def instr(self, line):
        m = re.match(r'^(\S+)\s*(.*)$', line)
        opc, rest = m.group(1), m.group(2)
        # sample_indexable(texture2d)(float,float,float,float) has its parts glued with no spaces
        sat = False
        base = opc
        mres = re.match(r'^([a-z0-9_]+?)(_indexable)?(\([^)]*\))?(\([^)]*\))?$', opc)
        if mres:
            base = mres.group(1)
        if base.endswith('_sat'):
            sat = True
            base = base[:-4]
        aoff = None
        ma = re.match(r'^(\w+?)_aoffimmi(?:_indexable)?\(([-\d]+),([-\d]+),([-\d]+)\)', opc)
        if ma:
            base = ma.group(1)
            aoff = (int(ma.group(2)), int(ma.group(3)), int(ma.group(4)))
        ops = [Op(x) for x in split_ops(rest)] if rest else []
        self.emit('// ' + line)
        if base in ('if_nz', 'if_z'):
            c = self.u(ops[0], 0)
            self.emit('if (%s%s) {' % ('' if base == 'if_nz' else '!', '(%s != 0u)' % c))
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
            self.emit('for (int guard_ = 0; guard_ < 65536; ++guard_) {')
            self.depth += 1
            return
        if base == 'break':
            self.emit('break;')
            return
        if base in ('breakc_nz', 'breakc_z'):
            self.emit('if (%s(%s != 0u)) break;' % ('' if base == 'breakc_nz' else '!', self.u(ops[0], 0)))
            return
        if base == 'continue':
            self.emit('continue;')
            return
        if base in ('continuec_nz', 'continuec_z'):
            self.emit('if (%s(%s != 0u)) continue;' % ('' if base == 'continuec_nz' else '!', self.u(ops[0], 0)))
            return
        if base == 'ret':
            self.emit('return;')
            return
        if base in ('retc_nz', 'retc_z'):
            self.emit('if (%s(%s != 0u)) return;' % ('' if base == 'retc_nz' else '!', self.u(ops[0], 0)))
            return
        if base in ('discard_nz', 'discard_z'):
            self.emit('if (%s(%s != 0u)) io.discarded = true;' % ('' if base == 'discard_nz' else '!', self.u(ops[0], 0)))
            return
        if base == 'switch':
            self.emit('switch ((int)%s) {' % self.u(ops[0], 0))
            self.depth += 1
            return
        if base == 'case':
            self.emit('case %d:' % (Op(rest).lits[0] if rest.startswith('l(') else int(rest, 0)))
            return
        if base == 'default':
            self.emit('default:')
            return
        if base in ('emit', 'cut', 'emit_stream', 'cut_stream', 'nop', 'sync_g', 'sync_uglobal'):
            return
        d = ops[0] if ops else None
        n = len(d.mask()) if d is not None and d.kind != 'null' else 0
        comps = d.mask() if d is not None and d.kind != 'null' else []
        if base == 'mov':
            if sat or ops[1].neg or ops[1].abs:
                self.write(d, [self.f(ops[1], c) for c in comps], sat)
            else:
                self.write(d, [self.lane(ops[1], c) for c in comps], kind='l')
            return
        if base == 'movc':
            ex = []
            for c in comps:
                ex.append('((%s != 0u) ? %s : %s)' % (self.u(ops[1], c), self.lane(ops[2], c), self.lane(ops[3], c)))
            self.write(d, ex, sat, kind='l')
            return
        if base == 'swapc':
            d1 = ops[1]
            for dd, (aa, bb) in ((d, (ops[3], ops[4])), (d1, (ops[4], ops[3]))):
                ex = ['((%s != 0u) ? %s : %s)' % (self.u(ops[2], c), self.lane(bb, c), self.lane(aa, c)) for c in dd.mask()]
                self.write(dd, ex, kind='l')
            return
        if base in FLOAT1:
            self.write(d, ['%s(%s)' % (FLOAT1[base], self.f(ops[1], c)) for c in comps], sat)
            return
        if base in FLOAT2:
            self.write(d, ['%s(%s, %s)' % (FLOAT2[base], self.f(ops[1], c), self.f(ops[2], c)) for c in comps], sat)
            return
        if base == 'mad':
            self.write(d, ['mad_(%s, %s, %s)' % (self.f(ops[1], c), self.f(ops[2], c), self.f(ops[3], c)) for c in comps], sat)
            return
        if base in FCMP:
            self.write(d, ['%s(%s, %s)' % (FCMP[base], self.f(ops[1], c), self.f(ops[2], c)) for c in comps], kind='u')
            return
        if base in ('dp2', 'dp3', 'dp4'):
            k = int(base[2])
            terms = ['mul_(%s, %s)' % (self.f(ops[1], i), self.f(ops[2], i)) for i in range(k)]
            # the operand swizzles index by source position i (0..k-1), not by the destination
            terms = []
            for i in range(k):
                terms.append('mul_(%s, %s)' % (self.fpos(ops[1], i), self.fpos(ops[2], i)))
            e = terms[0]
            for t in terms[1:]:
                e = 'add_(%s, %s)' % (e, t)
            self.write(d, [e] * n, sat)
            return
        if base == 'sincos':
            ds, dc = ops[0], ops[1]
            if ds.kind != 'null':
                self.write(ds, ['sin_(%s)' % self.f(ops[2], c) for c in ds.mask()], sat)
            if dc.kind != 'null':
                self.write(dc, ['cos_(%s)' % self.f(ops[2], c) for c in dc.mask()], sat)
            return
        if base in INT2:
            self.write(d, [INT2[base].format(a=self.u(ops[1], c), b=self.u(ops[2], c)) for c in comps], kind='u')
            return
        if base in INT1:
            self.write(d, [INT1[base].format(a=self.u(ops[1], c)) for c in comps], kind='u')
            return
        if base in INT3:
            self.write(d, [INT3[base].format(a=self.u(ops[1], c), b=self.u(ops[2], c), c=self.u(ops[3], c)) for c in comps], kind='u')
            return
        if base == 'bfi':
            self.write(d, ['bfi_(%s, %s, %s, %s)' % (self.u(ops[1], c), self.u(ops[2], c), self.u(ops[3], c), self.u(ops[4], c)) for c in comps], kind='u')
            return
        if base in F2I:
            self.write(d, ['%s(%s)' % (F2I[base], self.f(ops[1], c)) for c in comps], kind='u')
            return
        if base in I2F:
            self.write(d, ['%s(%s)' % (I2F[base], self.u(ops[1], c)) for c in comps], sat)
            return
        if base in ('imul', 'umul'):
            hi, lo = ops[0], ops[1]
            if hi.kind != 'null':
                f = '(uint32_t)(((int64_t)(int32_t){a} * (int64_t)(int32_t){b}) >> 32)' if base == 'imul' else '(uint32_t)(((uint64_t){a} * (uint64_t){b}) >> 32)'
                self.write(hi, [f.format(a=self.u(ops[2], c), b=self.u(ops[3], c)) for c in hi.mask()], kind='u')
            if lo.kind != 'null':
                self.write(lo, ['(%s * %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in lo.mask()], kind='u')
            return
        if base == 'udiv':
            q, rm = ops[0], ops[1]
            if q.kind != 'null':
                self.write(q, ['udiv_q(%s, %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in q.mask()], kind='u')
            if rm.kind != 'null':
                self.write(rm, ['udiv_r(%s, %s)' % (self.u(ops[2], c), self.u(ops[3], c)) for c in rm.mask()], kind='u')
            return
        if base in ('sample', 'sample_l', 'sample_b', 'sample_d', 'sample_c', 'sample_c_lz', 'gather4', 'gather4_c', 'lod'):
            self.sample(base, ops, sat, aoff)
            return
        if base in ('ld', 'ld_ms'):
            self.load(ops, sat, uint_ret='(uint' in opc)
            return
        if base == 'resinfo':
            self.resinfo(opc, ops)
            return
        if base in ('ld_structured', 'ld_raw', 'bufinfo', 'sampleinfo', 'samplepos'):
            # not in material code: zeros
            if d is not None and d.kind != 'null':
                self.write(d, ['0u'] * n, kind='u')
            return
        raise NotImplementedError(line)

    def fpos(self, o, i):
        """float source at swizzle position i (dp2/3/4 read their operands by position)"""
        k = o.swz[i] if len(o.swz) > 1 else o.swz[0]
        fake = Op.__new__(Op)
        fake.__dict__.update(o.__dict__)
        fake.swz = [k]
        return self.f(fake, 0)

    def coord(self, o, i):
        return self.fpos(o, i)

    def sample(self, base, ops, sat, aoff):
        d, co, t, s = ops[0], ops[1], ops[2], ops[3]
        ty = self.res.get(t.reg, 'texture2d')
        x, y, z = self.coord(co, 0), self.coord(co, 1), self.coord(co, 2)
        if base == 'lod':
            res = 'vec4(D(0.0), D(0.0), D(0.0), D(0.0))'
        elif ty == 'texture3d':
            res = 'tex3d(io, %d, %d, %s, %s, %s)' % (t.reg, s.reg, x, y, z)
        elif ty == 'texturecube':
            res = 'texcube(io, %d, %d, %s, %s, %s)' % (t.reg, s.reg, x, y, z)
        elif ty == 'texture2darray':
            res = 'tex2darr(io, %d, %d, %s, %s, %s)' % (t.reg, s.reg, x, y, z)
        elif ty == 'texturecubearray':
            res = 'texcubearr(io, %d, %d, %s, %s, %s, %s)' % (t.reg, s.reg, x, y, z, self.coord(co, 3))
        else:
            if aoff:
                x = 'add_(%s, D(%r))' % (x, aoff[0] * 0.001)
                y = 'add_(%s, D(%r))' % (y, aoff[1] * 0.001)
            res = 'tex2d(io, %d, %d, %s, %s)' % (t.reg, s.reg, x, y)
        if base in ('sample_c', 'sample_c_lz', 'gather4_c'):
            ref = self.f(ops[4], 0)
            res = 'cmp4_(%s, %s)' % (res, ref)
        self.emit('{ const vec4 tr_ = %s;' % res)
        self.depth += 1
        sw = t.swz if t.swz else [0, 1, 2, 3]
        names = ['tr_.x', 'tr_.y', 'tr_.z', 'tr_.w']
        ex = [names[sw[c] if len(sw) > 1 else sw[0]] for c in d.mask()]
        self.write(d, ex, sat)
        self.depth -= 1
        self.emit('}')

    def load(self, ops, sat, uint_ret=False):
        d, co, t = ops[0], ops[1], ops[2]
        ty = self.res.get(t.reg, 'texture2d')
        u = lambda i: self.upos(co, i)
        if ty == 'buffer' and uint_ret:
            # a uint buffer (the forward pass's light grid and light data): the driver's rows, their exact bits
            self.emit('{ const std::array<uint32_t, 4> tr_ = fetchbufU(io, %d, %s);' % (t.reg, u(0)))
            self.depth += 1
            sw = t.swz if t.swz else [0, 1, 2, 3]
            ex = ['tr_[%d]' % (sw[c] if len(sw) > 1 else sw[0]) for c in d.mask()]
            self.write(d, ex, kind='u')
            self.depth -= 1
            self.emit('}')
            return
        if ty == 'texture3d':
            res = 'fetch3d(io, %d, %s, %s, %s, %s)' % (t.reg, u(0), u(1), u(2), u(3))
        elif ty == 'buffer':
            res = 'fetchbuf(io, %d, %s)' % (t.reg, u(0))
        else:
            res = 'fetch2d(io, %d, %s, %s, %s)' % (t.reg, u(0), u(1), u(3) if ty == 'texture2d' else u(2))
        self.emit('{ const vec4 tr_ = %s;' % res)
        self.depth += 1
        sw = t.swz if t.swz else [0, 1, 2, 3]
        names = ['tr_.x', 'tr_.y', 'tr_.z', 'tr_.w']
        ex = [names[sw[c] if len(sw) > 1 else sw[0]] for c in d.mask()]
        self.write(d, ex, sat)
        self.depth -= 1
        self.emit('}')

    def upos(self, o, i):
        k = o.swz[i] if len(o.swz) > 1 else o.swz[0]
        fake = Op.__new__(Op)
        fake.__dict__.update(o.__dict__)
        fake.swz = [k]
        return self.u(fake, 0)

    def resinfo(self, opc, ops):
        d, mip, t = ops[0], ops[1], ops[2]
        self.emit('{ uint32_t w_, h_, l_; size2d(io, %d, %s, w_, h_, l_);' % (t.reg, self.upos(mip, 0)))
        self.depth += 1
        sw = t.swz if t.swz else [0, 1, 2, 3]
        vals = ['w_', 'h_', '1u', 'l_']
        uint = '_uint' in opc
        ex = []
        for c in d.mask():
            v = vals[sw[c] if len(sw) > 1 else sw[0]]
            ex.append(v if uint else 'utof_(%s)' % v)
        self.write(d, ex, kind='u' if uint else 'f')
        self.depth -= 1
        self.emit('}')


def translate(asm_text, name):
    return Gen(asm_text, name).translate()


if __name__ == '__main__':
    src = open(sys.argv[1], encoding='latin-1').read()
    code = translate(src, sys.argv[2])
    if len(sys.argv) > 3:
        open(sys.argv[3], 'w').write('#include "dxbc_cpu.hpp"\n' + code + '\n')
    else:
        print(code)
