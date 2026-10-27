"""A small DXBC (shader model 4/5) disassembler: signatures and the instruction stream as text, enough to read what a
pixel shader computes.

    python3 dxbcdis.py <file.dxbc>
"""
import struct
import sys

OPS = ('add and break breakc call callc case continue continuec cut default deriv_rtx deriv_rty discard div dp2 dp3 dp4 '
       'else emit emitthencut endif endloop endswitch eq exp frc ftoi ftou ge iadd if ieq ige ilt imad imax imin imul ine '
       'ineg ishl ishr itof label ld ld_ms log loop lt mad min max customdata mov movc mul ne nop not or resinfo ret retc '
       'round_ne round_ni round_pi round_z rsq sample sample_c sample_c_lz sample_l sample_d sample_b sqrt switch sincos '
       'udiv ult uge umul umad umax umin ushr utof xor dcl_resource dcl_constantbuffer dcl_sampler dcl_index_range '
       'dcl_outputtopology dcl_inputprimitive dcl_maxout dcl_input dcl_input_sgv dcl_input_siv dcl_input_ps '
       'dcl_input_ps_sgv dcl_input_ps_siv dcl_output dcl_output_sgv dcl_output_siv dcl_temps dcl_indexableTemp '
       'dcl_globalFlags reserved0 lod gather4 sample_pos sample_info reserved1 hs_decls hs_control_point_phase '
       'hs_fork_phase hs_join_phase emit_stream cut_stream emitthencut_stream interface_call bufinfo deriv_rtx_coarse '
       'deriv_rtx_fine deriv_rty_coarse deriv_rty_fine gather4_c gather4_po gather4_po_c rcp f32tof16 f16tof32 uaddc usubb '
       'countbits firstbit_hi firstbit_lo firstbit_shi ubfe ibfe bfi bfrev swapc dcl_stream dcl_function_body '
       'dcl_function_table dcl_interface dcl_input_control_point_count dcl_output_control_point_count dcl_tessellator_domain '
       'dcl_tessellator_partitioning dcl_tessellator_output_primitive dcl_hs_max_tessfactor '
       'dcl_hs_fork_phase_instance_count dcl_hs_join_phase_instance_count dcl_thread_group dcl_uav_typed dcl_uav_raw '
       'dcl_uav_structured dcl_tgsm_raw dcl_tgsm_structured dcl_resource_raw dcl_resource_structured ld_uav_typed '
       'store_uav_typed ld_raw store_raw ld_structured store_structured atomic_and atomic_or atomic_xor atomic_cmp_store '
       'atomic_iadd atomic_imax atomic_imin atomic_umax atomic_umin imm_atomic_alloc imm_atomic_consume imm_atomic_iadd '
       'imm_atomic_and imm_atomic_or imm_atomic_xor imm_atomic_exch imm_atomic_cmp_exch imm_atomic_imax imm_atomic_imin '
       'imm_atomic_umax imm_atomic_umin sync dadd dmax dmin dmul deq dge dlt dne dmov dmovc dtof ftod eval_snapped '
       'eval_sample_index eval_centroid dcl_gsinstances abort debug_break reserved2 ddiv dfma drcp msad dtoi dtou itod '
       'utod').split()
REG = {0: 'r', 1: 'v', 2: 'o', 3: 'x', 4: 'l', 5: 'd', 6: 's', 7: 't', 8: 'cb', 9: 'icb', 10: 'label',
       11: 'vPrim', 12: 'oDepth', 13: 'null', 14: 'rasterizer', 15: 'oMask', 16: 'stream', 17: 'function_body',
       18: 'function_table', 19: 'interface', 20: 'function_input', 21: 'function_output', 22: 'vOutputControlPointID',
       23: 'vForkInstanceID', 24: 'vJoinInstanceID', 25: 'vicp', 26: 'vocp', 27: 'patch_constant', 28: 'vDomain',
       29: 'this', 30: 'u', 31: 'g', 32: 'vThreadID', 33: 'vThreadGroupID', 34: 'vThreadIDInGroup', 35: 'vCoverage',
       36: 'vThreadIDInGroupFlattened', 37: 'vGSInstanceID', 38: 'oDepthGE', 39: 'oDepthLE', 40: 'vCycleCounter'}
SAT_OK = set(range(0, 120)) - {2, 3, 4, 5, 6, 7, 8, 13, 18, 21, 22, 23, 31, 44, 48, 53, 58, 62, 63, 76}
TEST_OPS = {'breakc', 'callc', 'continuec', 'if', 'discard', 'retc'}
INTERP = {0: '', 1: 'constant', 2: 'linear', 3: 'linear centroid', 4: 'linear noperspective',
          5: 'linear noperspective centroid', 6: 'linear sample', 7: 'linear noperspective sample'}
DIM = {0: 'unknown', 1: 'buffer', 2: 'texture1d', 3: 'texture2d', 4: 'texture2dms', 5: 'texture3d', 6: 'texturecube',
       7: 'texture1darray', 8: 'texture2darray', 9: 'texture2dmsarray', 10: 'texturecubearray', 11: 'raw_buffer',
       12: 'structured_buffer'}


def f32(u):
    return struct.unpack('<f', struct.pack('<I', u))[0]


def fmt_imm(u):
    f = f32(u)
    if u == 0:
        return '0'
    if abs(f) >= 1e-6 and abs(f) < 1e9 and f == f:
        return ('%.6g' % f)
    return '0x%08x' % u


class Dis(object):
    def __init__(self, tokens):
        self.t = tokens
        self.p = 0

    def tok(self):
        v = self.t[self.p]
        self.p += 1
        return v

    def operand(self):
        o = self.tok()
        ncomp = o & 3
        sel = (o >> 2) & 3
        typ = (o >> 12) & 0xFF
        idim = (o >> 20) & 3
        reps = [(o >> 22) & 7, (o >> 25) & 7, (o >> 28) & 7]
        mod = ''
        ext = o >> 31
        while ext:
            e = self.tok()
            if e & 0x3F == 1:
                m = (e >> 6) & 0xFF
                mod = {0: '', 1: 'neg', 2: 'abs', 3: 'negabs'}.get(m, '?')
            ext = e >> 31
        comps = ''
        if ncomp == 2:
            if sel == 0:
                m = (o >> 4) & 0xF
                comps = '.' + ''.join(c for i, c in enumerate('xyzw') if m >> i & 1) if m != 0xF else ''
            elif sel == 1:
                sw = (o >> 4) & 0xFF
                comps = '.' + ''.join('xyzw'[(sw >> (2 * i)) & 3] for i in range(4))
            else:
                comps = '.' + 'xyzw'[(o >> 4) & 3]
        if typ == 4:   # immediate32
            n = 1 if ncomp == 1 else 4
            vals = [self.tok() for _ in range(n)]
            s = 'l(%s)' % ', '.join(fmt_imm(v) for v in vals)
            return self._mod(s, mod)
        if typ == 5:
            n = 1 if ncomp == 1 else 2
            vals = [self.tok() | (self.tok() << 32) for _ in range(n)]
            return 'd(%s)' % ', '.join('0x%x' % v for v in vals)
        name = REG.get(typ, 'op%d' % typ)
        idx = []
        for d in range(idim):
            r = reps[d]
            if r == 0:
                idx.append(str(self.tok()))
            elif r == 1:
                idx.append(str(self.tok() | (self.tok() << 32)))
            elif r == 2:
                idx.append(self.operand())
            elif r == 3:
                base = self.tok()
                idx.append('%s + %d' % (self.operand(), base))
            else:
                base = self.tok() | (self.tok() << 32)
                idx.append('%s + %d' % (self.operand(), base))
        if not idx:
            s = name
        elif typ in (0, 1, 2, 6, 7, 30, 31) and idim == 1 and reps[0] == 0:
            s = '%s%s' % (name, idx[0])
        else:
            s = name + (idx[0] if typ in (8, 3) and not idx[0].startswith(('r', 'v')) else '') + ''.join(
                '[%s]' % i for i in (idx[1:] if typ in (8, 3) and not idx[0].startswith(('r', 'v')) else idx))
        return self._mod(s + comps, mod)

    @staticmethod
    def _mod(s, mod):
        if mod == 'neg':
            return '-' + s
        if mod == 'abs':
            return '|' + s + '|'
        if mod == 'negabs':
            return '-|' + s + '|'
        return s

    def run(self):
        ver = self.tok()
        length = self.tok()
        kind = {0: 'ps', 1: 'vs', 2: 'gs', 3: 'hs', 4: 'ds', 5: 'cs'}.get(ver >> 16, '?')
        out = ['%s_%d_%d' % (kind, (ver >> 4) & 0xF, ver & 0xF)]
        indent = 0
        n = 0
        while self.p < length:
            start = self.p
            op = self.tok()
            code = op & 0x7FF
            name = OPS[code] if code < len(OPS) else 'op%d' % code
            if name == 'customdata':
                ln = self.tok()
                cls = op >> 11
                if cls == 3:   # immediate constant buffer
                    vals = self.t[self.p:start + ln]
                    out.append('dcl_immediateConstantBuffer { %s }' % ', '.join(fmt_imm(v) for v in vals[:64]))
                else:
                    out.append('customdata class %d (%d dwords)' % (cls, ln))
                self.p = start + ln
                continue
            ln = (op >> 24) & 0x7F
            ext = op >> 31
            extras = []
            while ext:
                e = self.tok()
                et = e & 0x3F
                if et == 1:
                    def s4(v):
                        return v - 16 if v & 8 else v
                    extras.append('(%d,%d,%d)' % (s4((e >> 9) & 0xF), s4((e >> 13) & 0xF), s4((e >> 17) & 0xF)))
                elif et == 2:
                    extras.append('(%s)' % DIM.get((e >> 6) & 0x1F, '?'))
                elif et == 3:
                    extras.append('(rettype)')
                ext = e >> 31
            end = start + ln
            if name in ('else', 'endif', 'endloop', 'endswitch', 'case', 'default'):
                indent = max(0, indent - 1)
            text = name
            if name == 'dcl_temps':
                text += ' %d' % self.tok()
            elif name == 'dcl_globalFlags':
                text += ' 0x%x' % ((op >> 11) & 0x1FFF)
            elif name == 'dcl_indexableTemp':
                text += ' x%d[%d], %d' % (self.tok(), self.tok(), self.tok())
            elif name == 'dcl_resource':
                text += '_%s %s' % (DIM.get((op >> 11) & 0x1F, '?'), self.operand())
                self.p = end
            elif name == 'dcl_constantbuffer':
                text += ' %s%s' % (self.operand(), ', dynamicIndexed' if (op >> 11) & 1 else '')
            elif name == 'dcl_sampler':
                text += ' %s%s' % (self.operand(), {0: '', 1: ', mode_comparison', 2: ', mode_mono'}.get((op >> 11) & 0xF, ''))
            elif name in ('dcl_input_ps', 'dcl_input_ps_siv', 'dcl_input_ps_sgv'):
                text += ' %s %s' % (INTERP.get((op >> 11) & 0xF, '?'), self.operand())
                if name != 'dcl_input_ps':
                    text += ', sv%d' % self.tok()
            elif name in ('dcl_output_siv', 'dcl_output_sgv', 'dcl_input_siv', 'dcl_input_sgv'):
                text += ' %s, sv%d' % (self.operand(), self.tok())
            elif name.startswith('dcl_') and name not in ('dcl_input', 'dcl_output', 'dcl_index_range'):
                self.p = end
            else:
                ops = []
                if (op >> 13) & 1 and code in SAT_OK and not name.startswith('dcl'):
                    text += '_sat'
                if name in TEST_OPS:
                    text += '_nz' if (op >> 18) & 1 else '_z'
                if name in ('sample', 'sample_l', 'sample_b', 'sample_d', 'sample_c', 'sample_c_lz', 'ld', 'gather4'):
                    text += ''.join(extras)
                while self.p < end:
                    ops.append(self.operand())
                text += ' ' + ', '.join(ops) if ops else ''
            self.p = end
            if not name.startswith('dcl'):
                n += 1
                out.append('%4d: %s%s' % (n, '  ' * indent, text))
            else:
                out.append('      ' + text)
            if name in ('if', 'else', 'loop', 'switch', 'case', 'default'):
                indent += 1
        return out


def chunks(blob):
    count = struct.unpack_from('<I', blob, 28)[0]
    out = {}
    for i in range(count):
        off = struct.unpack_from('<I', blob, 32 + 4 * i)[0]
        out[blob[off:off + 4].decode('latin1')] = blob[off + 8:off + 8 + struct.unpack_from('<I', blob, off + 4)[0]]
    return out


def signature(data, tag):
    count = struct.unpack_from('<I', data, 0)[0]
    step = 24 if tag in ('ISGN', 'OSGN', 'PCSG') else 28
    out = []
    for i in range(count):
        base = 8 + i * step
        if step == 28:
            stream, name_off, sem_idx, sv, ctype, reg = struct.unpack_from('<IIIIII', data, base)
            mask, rw = data[base + 24], data[base + 25]
        else:
            name_off, sem_idx, sv, ctype, reg = struct.unpack_from('<IIIII', data, base)
            mask, rw = data[base + 20], data[base + 21]
        name = data[name_off:data.index(b'\0', name_off)].decode()
        comps = ''.join(c for j, c in enumerate('xyzw') if mask >> j & 1)
        used = ''.join(c for j, c in enumerate('xyzw') if rw >> j & 1)
        out.append('%s%d -> reg %d .%s (used .%s)%s' % (name, sem_idx, reg, comps, used, ' sv%d' % sv if sv else ''))
    return out


def disassemble(blob):
    ch = chunks(blob)
    lines = []
    for tag in ('ISGN', 'OSGN', 'OSG5'):
        if tag in ch:
            lines.append('// %s' % tag)
            lines += ['//   ' + s for s in signature(ch[tag], tag)]
    code = ch.get('SHEX') or ch.get('SHDR')
    n = len(code) // 4
    lines += Dis(list(struct.unpack('<%dI' % n, code[:n * 4]))).run()
    return '\n'.join(lines)


if __name__ == '__main__':
    print(disassemble(open(sys.argv[1], 'rb').read()))
