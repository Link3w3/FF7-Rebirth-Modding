"""UE 4.26 VectorVM bytecode (also Rebirth's: the same 96 opcodes) — disassembler, and operand rewriting.

    vvm.py <script bytes file> [ext function register counts, comma separated]
Encoding (VectorVM.cpp): u8 op, then
  unary/binary/trinary kernels: u8 source operand types (bit k: input k is a constant), u16 per input, u16 dest
  inputdata_*/inputdata_noadvance_*: u16 dataset, u16 input register, u16 dest
  outputdata_*: u8 types, u16 dataset, u16 dest index register, u16 source (register or constant), u16 dest register
  acquireindex: u8 types, u16 dataset, u16 valid (constant when types bit 0), u16 dest
  external_func_call: u8 function index, then (inputs + outputs of that function) u16 (bit 15 set: register)
  exec_index: u16 dest;  enter_stat_scope: u16 constant;  exit_stat_scope: -
  update_id / acquire_id: u16 dataset, u16, u16
Constants are byte offsets into the concatenation of the constant buffers (global, system, owner, emitter, external
parameters, [the same five for the previous frame when spawning interpolated], script literals).
"""
import struct, sys

OPS = ['done', 'add', 'sub', 'mul', 'div', 'mad', 'lerp', 'rcp', 'rsq', 'sqrt', 'neg', 'abs', 'exp', 'exp2', 'log', 'log2',
       'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2', 'ceil', 'floor', 'fmod', 'frac', 'trunc', 'clamp', 'min', 'max',
       'pow', 'round', 'sign', 'step', 'random', 'noise', 'cmplt', 'cmple', 'cmpgt', 'cmpge', 'cmpeq', 'cmpneq', 'select',
       'addi', 'subi', 'muli', 'divi', 'clampi', 'mini', 'maxi', 'absi', 'negi', 'signi', 'randomi', 'cmplti', 'cmplei',
       'cmpgti', 'cmpgei', 'cmpeqi', 'cmpneqi', 'bit_and', 'bit_or', 'bit_xor', 'bit_not', 'bit_lshift', 'bit_rshift',
       'logic_and', 'logic_or', 'logic_xor', 'logic_not', 'f2i', 'i2f', 'f2b', 'b2f', 'i2b', 'b2i', 'inputdata_float',
       'inputdata_int32', 'inputdata_half', 'inputdata_noadvance_float', 'inputdata_noadvance_int32',
       'inputdata_noadvance_half', 'outputdata_float', 'outputdata_int32', 'outputdata_half', 'acquireindex',
       'external_func_call', 'exec_index', 'noise2D', 'noise3D', 'enter_stat_scope', 'exit_stat_scope', 'update_id',
       'acquire_id']
OP = {n: i for i, n in enumerate(OPS)}
UNARY = {'rcp', 'rsq', 'sqrt', 'neg', 'abs', 'exp', 'exp2', 'log', 'log2', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
         'ceil', 'floor', 'frac', 'trunc', 'sign', 'step', 'round', 'random', 'noise', 'absi', 'negi', 'signi', 'randomi',
         'bit_not', 'logic_not', 'f2i', 'i2f', 'f2b', 'b2f', 'i2b', 'b2i'}
BINARY = {'add', 'sub', 'mul', 'div', 'fmod', 'min', 'max', 'pow', 'atan2', 'cmplt', 'cmple', 'cmpgt', 'cmpge',
          'cmpeq', 'cmpneq', 'addi', 'subi', 'muli', 'divi', 'mini', 'maxi', 'cmplti', 'cmplei', 'cmpgti', 'cmpgei',
          'cmpeqi', 'cmpneqi', 'bit_and', 'bit_or', 'bit_xor', 'bit_lshift', 'bit_rshift', 'logic_and', 'logic_or',
          'logic_xor', 'noise2D'}
TRINARY = {'mad', 'lerp', 'clamp', 'select', 'clampi', 'noise3D'}
INPUT = {'inputdata_float', 'inputdata_int32', 'inputdata_half', 'inputdata_noadvance_float', 'inputdata_noadvance_int32',
         'inputdata_noadvance_half'}
OUTPUT = {'outputdata_float', 'outputdata_int32', 'outputdata_half'}


class Ins:
    __slots__ = ('at', 'op', 'types', 'operands', 'size')

    def __init__(self, at, op, types, operands, size):
        self.at, self.op, self.types, self.operands, self.size = at, op, types, operands, size

    def __repr__(self):
        ops = []
        for kind, pos, v in self.operands:
            ops.append({'c': 'c%d' % v, 'r': 'r%d' % v, 'd': 'd%d' % v, 'x': '#%d' % v, 'o': 'o%d' % (v & 0x7fff), 'e': 'e%s' % (
                ('r%d' % (v & 0x7fff)) if v & 0x8000 else ('c%d' % v))}[kind])
        return '%5d %-26s %s' % (self.at, self.op, ' '.join(ops))


def decode(code, ext_counts=None):
    """-> [Ins]. ext_counts: per external function (inputs, outputs). operands: (kind, byte position, value); kind: 'c'
    constant byte offset, 'r' register (input), 'd' destination register, 'x' other index, 'e' external function input
    (bit 15: register, else constant), 'o' external function output register."""
    out = []
    p = 0
    n = len(code)
    while p < n:
        at = p
        op = code[p]; p += 1
        if op >= len(OPS):
            raise ValueError('bad opcode %d at %d' % (op, at))
        name = OPS[op]
        operands = []
        types = None

        def u16(kind):
            nonlocal p
            v = struct.unpack_from('<H', code, p)[0]
            operands.append((kind, p, v)); p += 2

        if name == 'done':
            out.append(Ins(at, name, None, [], 1))
            break
        if name in UNARY or name in BINARY or name in TRINARY:
            k = 1 if name in UNARY else 2 if name in BINARY else 3
            types = code[p]; p += 1
            for j in range(k):
                u16('c' if types & (1 << j) else 'r')
            u16('d')
        elif name in INPUT:
            u16('x'); u16('x'); u16('d')
        elif name in OUTPUT:
            types = code[p]; p += 1
            u16('x'); u16('r'); u16('c' if types & 1 else 'r'); u16('x')
        elif name == 'acquireindex':
            # TBinaryKernelHandler<Dst, FDataSetCounterHandler, valid>: SRCOP_RRC (bit 0) = the valid flag is a constant
            types = code[p]; p += 1
            u16('x'); u16('c' if types & 1 else 'r'); u16('d')
        elif name == 'external_func_call':
            fi = code[p]; p += 1
            operands.append(('x', p - 1, fi))
            cnt = ext_counts[fi] if ext_counts is not None and fi < len(ext_counts) else None
            if cnt is None:
                raise ValueError('external function %d register count unknown (at %d)' % (fi, at))
            nin, nout = cnt if isinstance(cnt, tuple) else (cnt, 0)
            for _ in range(nin):
                u16('e')          # input: bit 15 set = register, else a constant
            for _ in range(nout):
                u16('o')          # output register
        elif name == 'exec_index':
            u16('d')
        elif name == 'enter_stat_scope':
            u16('c')
        elif name == 'exit_stat_scope':
            pass
        elif name in ('update_id', 'acquire_id'):
            u16('x'); u16('r'); u16('r')
        else:
            raise ValueError('unhandled op %s at %d' % (name, at))
        out.append(Ins(at, name, types, operands, p - at))
    return out


def constants(ins):
    """[(byte position in code, constant offset)] of every constant operand"""
    res = []
    for i in ins:
        for kind, pos, v in i.operands:
            if kind == 'c' or (kind == 'e' and not v & 0x8000):
                res.append((pos, v))
    return res


def remap_constants(code, ins, fn):
    """code with every constant operand v replaced by fn(v)"""
    b = bytearray(code)
    for i in ins:
        for kind, pos, v in i.operands:
            if kind == 'c':
                nv = fn(v)
                assert 0 <= nv < 0x10000
                struct.pack_into('<H', b, pos, nv)
            elif kind == 'e' and not v & 0x8000:
                nv = fn(v)
                assert 0 <= nv < 0x8000
                struct.pack_into('<H', b, pos, nv)
    return bytes(b)


if __name__ == '__main__':
    code = open(sys.argv[1], 'rb').read()
    counts = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else None
    for i in decode(code, counts):
        print(i)
