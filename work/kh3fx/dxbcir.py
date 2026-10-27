"""DXBC shader model 4/5 bytecode -> a list of instructions with structured operands (for translation to HLSL), plus
the input/output signatures.

    parse(blob) -> dict(inputs=[Sig], outputs=[Sig], decls=[Instr], code=[Instr])
"""
import struct
from collections import namedtuple

from dxbcdis import OPS, chunks, SAT_OK, TEST_OPS

Sig = namedtuple('Sig', 'name index reg mask used sv')


class Operand(object):
    __slots__ = ('file', 'index', 'comps', 'mod', 'imm', 'ncomp', 'sel')

    def __repr__(self):
        if self.file == 'l':
            return 'l(%s)' % ','.join('%08x' % v for v in self.imm)
        return '%s%s%s.%s' % ('-' if 'neg' in self.mod else '', self.file, self.index, self.comps)


class Instr(object):
    __slots__ = ('op', 'sat', 'test', 'ops', 'dim', 'offsets', 'raw', 'controls')

    def __repr__(self):
        return '%s%s%s %s' % (self.op, '_sat' if self.sat else '', ('_' + self.test) if self.test else '',
                              ', '.join(repr(o) for o in self.ops))


def _sig(data, tag):
    count = struct.unpack_from('<I', data, 0)[0]
    step = 24 if tag in ('ISGN', 'OSGN', 'PCSG') else 28
    out = []
    for i in range(count):
        base = 8 + i * step
        if step == 28:
            _, name_off, sem_idx, sv, ctype, reg = struct.unpack_from('<IIIIII', data, base)
            mask, rw = data[base + 24], data[base + 25]
        else:
            name_off, sem_idx, sv, ctype, reg = struct.unpack_from('<IIIII', data, base)
            mask, rw = data[base + 20], data[base + 21]
        name = data[name_off:data.index(b'\0', name_off)].decode()
        out.append(Sig(name, sem_idx, reg, mask, rw, sv))
    return out


class _P(object):
    def __init__(self, toks):
        self.t, self.p = toks, 0

    def tok(self):
        v = self.t[self.p]
        self.p += 1
        return v

    def operand(self):
        o = self.tok()
        op = Operand()
        op.ncomp = o & 3
        op.sel = (o >> 2) & 3
        typ = (o >> 12) & 0xFF
        idim = (o >> 20) & 3
        reps = [(o >> 22) & 7, (o >> 25) & 7, (o >> 28) & 7]
        op.mod = ''
        ext = o >> 31
        while ext:
            e = self.tok()
            if e & 0x3F == 1:
                op.mod = {0: '', 1: 'neg', 2: 'abs', 3: 'negabs'}.get((e >> 6) & 0xFF, '')
            ext = e >> 31
        op.comps = ''
        if op.ncomp == 2:
            if op.sel == 0:
                m = (o >> 4) & 0xF
                op.comps = ''.join(c for i, c in enumerate('xyzw') if m >> i & 1)
            elif op.sel == 1:
                sw = (o >> 4) & 0xFF
                op.comps = ''.join('xyzw'[(sw >> (2 * i)) & 3] for i in range(4))
            else:
                op.comps = 'xyzw'[(o >> 4) & 3] * 4
        elif op.ncomp == 1:
            op.comps = 'xxxx'
        op.imm = None
        if typ == 4:
            n = 1 if op.ncomp == 1 else 4
            op.imm = [self.tok() for _ in range(n)]
            if n == 1:
                op.imm = op.imm * 4
            op.file, op.index = 'l', []
            return op
        if typ == 5:
            n = 1 if op.ncomp == 1 else 2
            op.imm = [self.tok() | (self.tok() << 32) for _ in range(n)]
            op.file, op.index = 'd', []
            return op
        op.file = {0: 'r', 1: 'v', 2: 'o', 3: 'x', 6: 's', 7: 't', 8: 'cb', 9: 'icb', 12: 'oDepth', 13: 'null',
                   35: 'vCoverage'}.get(typ, 'op%d' % typ)
        op.index = []
        for d in range(idim):
            r = reps[d]
            if r == 0:
                op.index.append(self.tok())
            elif r == 1:
                op.index.append(self.tok() | (self.tok() << 32))
            elif r == 2:
                op.index.append(('rel', self.operand(), 0))
            elif r == 3:
                base = self.tok()
                op.index.append(('rel', self.operand(), base))
            else:
                base = self.tok() | (self.tok() << 32)
                op.index.append(('rel', self.operand(), base))
        return op


def parse(blob):
    ch = chunks(blob)
    res = dict(inputs=_sig(ch['ISGN'], 'ISGN') if 'ISGN' in ch else [],
               outputs=_sig(ch['OSGN'], 'OSGN') if 'OSGN' in ch else [], decls=[], code=[])
    code = ch.get('SHEX') or ch.get('SHDR')
    n = len(code) // 4
    p = _P(list(struct.unpack('<%dI' % n, code[:n * 4])))
    p.tok()
    length = p.tok()
    while p.p < length:
        start = p.p
        tok = p.tok()
        opc = tok & 0x7FF
        name = OPS[opc] if opc < len(OPS) else 'op%d' % opc
        if name == 'customdata':
            ln = p.tok()
            p.p = start + ln
            continue
        ln = (tok >> 24) & 0x7F
        ins = Instr()
        ins.op, ins.controls = name, (tok >> 11) & 0x1FFF
        ins.sat = bool((tok >> 13) & 1) and opc in SAT_OK and not name.startswith('dcl')
        ins.test = ('nz' if (tok >> 18) & 1 else 'z') if name in TEST_OPS else ''
        ins.dim, ins.offsets = None, None
        ext = tok >> 31
        while ext:
            e = p.tok()
            if e & 0x3F == 1:
                def s4(v):
                    return v - 16 if v & 8 else v
                ins.offsets = (s4((e >> 9) & 0xF), s4((e >> 13) & 0xF), s4((e >> 17) & 0xF))
            elif e & 0x3F == 2:
                ins.dim = (e >> 6) & 0x1F
            ext = e >> 31
        end = start + ln
        ins.ops = []
        if name.startswith('dcl'):
            ins.raw = p.t[p.p:end]
            p.p = end
            res['decls'].append(ins)
            continue
        while p.p < end:
            ins.ops.append(p.operand())
        p.p = end
        res['code'].append(ins)
    return res
