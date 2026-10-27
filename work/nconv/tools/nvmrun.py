"""A numpy interpreter for UE 4.26 VectorVM byte code (Rebirth's VM runs the same code): runs a script over N
instances with given constant buffers, input datasets and external functions, to check what converted scripts compute
(and what the game's own scripts write) without the game.

Semantics follow VectorVM.cpp (4.26): registers are 32-bit (floats and ints share them, compares give all-bits masks),
'safe' div/rcp/sqrt/log/pow give 0 where the input is out of range, f2i truncates, random draws uniform [0,1) * x.

    run = VM(code, ext_counts, num_temp_registers)
    out = run(n, constants=bytes, inputs={dataset: {'f': float32[ncomp, n], 'i': int32[ncomp, n]}},
              outputs={dataset: (nfloat, nint)}, functions=[callable(inputs list, n) -> outputs list])
    out[dataset]['f'] / ['i']: the written components (NaN / -1 where never written), out[dataset]['count']
"""
import struct
import numpy as np
import nvvm

SMALL = np.float32(1e-8)


class VMError(Exception):
    pass


class VM:
    def __init__(self, code, ext_counts, num_temp_registers):
        self.ins = nvvm.decode(code, ext_counts)
        self.ext_counts = ext_counts
        self.ntemp = num_temp_registers

    def __call__(self, n, constants, inputs=None, outputs=None, functions=(), rng=None, exec_start=0, trace=None):
        rng = rng or np.random.default_rng(1)
        consts = np.frombuffer(bytes(constants) + b'\0' * 4, dtype=np.uint32)
        regs = np.zeros((max(self.ntemp, 1), n), dtype=np.uint32)
        inputs = inputs or {}
        outputs = outputs or {}
        out = {}
        for ds, (nf, ni) in outputs.items():
            out[ds] = {'f': np.full((nf, n), np.nan, dtype=np.float32), 'i': np.full((ni, n), -1, dtype=np.int32),
                       'count': 0, 'written_f': set(), 'written_i': set()}
        counters = {ds: -1 for ds in outputs}

        def c_u32(off):
            if off % 4:
                raise VMError('unaligned constant offset %d' % off)
            return consts[off // 4]

        def src(kind, v):
            if kind == 'c':
                return np.full(n, c_u32(v), dtype=np.uint32)
            if kind == 'r':
                return regs[v]
            raise VMError('bad source kind %s' % kind)

        f = lambda a: a.view(np.float32)
        i = lambda a: a.view(np.int32)
        u = lambda a: np.ascontiguousarray(a).view(np.uint32)
        mask = lambda b: np.where(b, np.uint32(0xFFFFFFFF), np.uint32(0))

        with np.errstate(all='ignore'):
            for ins in self.ins:
                op = ins.op
                ops = ins.operands
                if op == 'done':
                    break
                if op in ('enter_stat_scope', 'exit_stat_scope'):
                    continue
                if op in nvvm.UNARY or op in nvvm.BINARY or op in nvvm.TRINARY:
                    a = [src(k, v) for k, p, v in ops[:-1]]
                    d = ops[-1][2]
                    regs[d] = self.kernel(op, a, n, rng, f, i, u, mask)
                elif op in nvvm.INPUT:
                    ds, comp, d = ops[0][2], ops[1][2], ops[2][2]
                    kind = 'f' if 'float' in op else 'i'
                    data = inputs.get(ds, {}).get(kind)
                    if data is None or comp >= len(data):
                        raise VMError('input %s component %d of dataset %d missing' % (kind, comp, ds))
                    col = data[comp]
                    if 'noadvance' in op:
                        col = np.full(n, col[0], dtype=col.dtype)
                    else:
                        col = col[exec_start:exec_start + n]
                    regs[d] = u(col)
                elif op == 'acquireindex':
                    ds, (vk, vp, vv), d = ops[0][2], ops[1], ops[2][2]
                    valid = src(vk, vv) != 0
                    idx = np.full(n, -1, dtype=np.int32)
                    k = int(valid.sum())
                    base = counters.setdefault(ds, -1)
                    idx[valid] = np.arange(base + 1, base + 1 + k, dtype=np.int32)
                    counters[ds] = base + k
                    regs[d] = u(idx)
                elif op in nvvm.OUTPUT:
                    ds, ireg, (sk, sp, sv), comp = ops[0][2], ops[1][2], ops[2], ops[3][2]
                    kind = 'f' if 'float' in op else 'i'
                    dest = i(regs[ireg])
                    val = src(sk, sv)
                    o = out.get(ds)
                    if o is None:
                        raise VMError('output dataset %d not given' % ds)
                    arr = o[kind]
                    if comp >= len(arr):
                        raise VMError('output %s component %d of dataset %d beyond %d' % (kind, comp, ds, len(arr)))
                    ok = dest >= 0
                    arr[comp][dest[ok]] = (f(val) if kind == 'f' else i(val))[ok]
                    o['written_' + kind].add(comp)
                elif op == 'exec_index':
                    regs[ops[0][2]] = u(np.arange(exec_start, exec_start + n, dtype=np.int32))
                elif op == 'external_func_call':
                    fi = ops[0][2]
                    nin, nout = self.ext_counts[fi]
                    args = []
                    for k, p, v in ops[1:1 + nin]:
                        args.append(regs[v & 0x7fff] if v & 0x8000 else np.full(n, c_u32(v), dtype=np.uint32))
                    fn = functions[fi] if fi < len(functions) else None
                    if fn is None:
                        raise VMError('external function %d not bound' % fi)
                    res = fn([f(a) for a in args], n)
                    if len(res) != nout:
                        raise VMError('external function %d gave %d outputs, wants %d' % (fi, len(res), nout))
                    for (k, p, v), r in zip(ops[1 + nin:], res):
                        if v == 0xFFFF:              # (an output the script does not use: INDEX_NONE)
                            continue
                        regs[v & 0x7fff] = u(np.asarray(r, dtype=np.float32 if r.dtype.kind == 'f' else np.int32))
                elif op in ('update_id', 'acquire_id'):
                    raise VMError('persistent IDs not supported')
                else:
                    raise VMError('op %s not supported' % op)
                if trace is not None:
                    trace(ins, regs)
        for ds, o in out.items():
            o['count'] = counters.get(ds, -1) + 1
        return out

    @staticmethod
    def kernel(op, a, n, rng, f, i, u, mask):
        if op == 'add': return u(f(a[0]) + f(a[1]))
        if op == 'sub': return u(f(a[0]) - f(a[1]))
        if op == 'mul': return u(f(a[0]) * f(a[1]))
        if op == 'div':
            b = f(a[1]); return u(np.where(np.abs(b) > SMALL, f(a[0]) / np.where(b == 0, 1, b), 0).astype(np.float32))
        if op == 'mad': return u(f(a[0]) * f(a[1]) + f(a[2]))
        if op == 'lerp': return u(f(a[0]) * (1 - f(a[2])) + f(a[1]) * f(a[2]))
        if op == 'rcp':
            x = f(a[0]); return u(np.where(np.abs(x) > SMALL, 1 / np.where(x == 0, 1, x), 0).astype(np.float32))
        if op == 'rsq':
            x = f(a[0]); return u(np.where(x > SMALL, 1 / np.sqrt(np.maximum(x, SMALL)), 0).astype(np.float32))
        if op == 'sqrt':
            x = f(a[0]); return u(np.where(x > SMALL, np.sqrt(np.maximum(x, 0)), 0).astype(np.float32))
        if op == 'neg': return u(-f(a[0]))
        if op == 'abs': return u(np.abs(f(a[0])))
        if op == 'exp': return u(np.exp(f(a[0])))
        if op == 'exp2': return u(np.exp2(f(a[0])))
        if op == 'log':
            x = f(a[0]); return u(np.where(x > 0, np.log(np.maximum(x, SMALL)), 0).astype(np.float32))
        if op == 'log2': return u(np.log2(f(a[0])))
        if op == 'sin': return u(np.sin(f(a[0])))
        if op == 'cos': return u(np.cos(f(a[0])))
        if op == 'tan': return u(np.tan(f(a[0])))
        if op == 'asin': return u(np.arcsin(f(a[0])))
        if op == 'acos': return u(np.arccos(f(a[0])))
        if op == 'atan': return u(np.arctan(f(a[0])))
        if op == 'atan2': return u(np.arctan2(f(a[0]), f(a[1])))
        if op == 'ceil': return u(np.ceil(f(a[0])))
        if op == 'floor': return u(np.floor(f(a[0])))
        if op == 'round':
            x = f(a[0]); t = np.trunc(x); return u((t + np.trunc((x - t) * np.float32(1.9999999))).astype(np.float32))
        if op == 'fmod':
            x, y = f(a[0]), f(a[1]); return u(np.fmod(x, y).astype(np.float32))
        if op == 'frac':
            x = f(a[0]); return u((x - np.trunc(x)).astype(np.float32))
        if op == 'trunc': return u(np.trunc(f(a[0])))
        if op == 'clamp': return u(np.minimum(np.maximum(f(a[0]), f(a[1])), f(a[2])))
        if op == 'min': return u(np.minimum(f(a[0]), f(a[1])))
        if op == 'max': return u(np.maximum(f(a[0]), f(a[1])))
        if op == 'pow':
            x, y = f(a[0]), f(a[1]); return u(np.where(x > SMALL, np.power(np.maximum(x, SMALL), y), 0).astype(np.float32))
        if op == 'sign': return u(np.where(f(a[0]) >= 0, 1, -1).astype(np.float32))
        if op == 'step': return u(np.where(f(a[0]) >= 0, 1, 0).astype(np.float32))
        if op == 'random': return u((rng.random(n, dtype=np.float32) * f(a[0])).astype(np.float32))
        if op == 'cmplt': return mask(f(a[0]) < f(a[1]))
        if op == 'cmple': return mask(f(a[0]) <= f(a[1]))
        if op == 'cmpgt': return mask(f(a[0]) > f(a[1]))
        if op == 'cmpge': return mask(f(a[0]) >= f(a[1]))
        if op == 'cmpeq': return mask(f(a[0]) == f(a[1]))
        if op == 'cmpneq': return mask(f(a[0]) != f(a[1]))
        if op == 'select': return (a[0] & a[1]) | (~a[0] & a[2])
        if op == 'addi': return u(i(a[0]) + i(a[1]))
        if op == 'subi': return u(i(a[0]) - i(a[1]))
        if op == 'muli': return u(i(a[0]) * i(a[1]))
        if op == 'divi':
            x, y = i(a[0]), i(a[1]); return u(np.where(y != 0, np.trunc(x / np.where(y == 0, 1, y)), 0).astype(np.int32))
        if op == 'clampi': return u(np.minimum(np.maximum(i(a[0]), i(a[1])), i(a[2])))
        if op == 'mini': return u(np.minimum(i(a[0]), i(a[1])))
        if op == 'maxi': return u(np.maximum(i(a[0]), i(a[1])))
        if op == 'absi': return u(np.abs(i(a[0])))
        if op == 'negi': return u(-i(a[0]))
        if op == 'signi': return u(np.sign(i(a[0])).astype(np.int32))
        if op == 'randomi': return u((rng.random(n) * i(a[0])).astype(np.int32))
        if op == 'cmplti': return mask(i(a[0]) < i(a[1]))
        if op == 'cmplei': return mask(i(a[0]) <= i(a[1]))
        if op == 'cmpgti': return mask(i(a[0]) > i(a[1]))
        if op == 'cmpgei': return mask(i(a[0]) >= i(a[1]))
        if op == 'cmpeqi': return mask(i(a[0]) == i(a[1]))
        if op == 'cmpneqi': return mask(i(a[0]) != i(a[1]))
        if op in ('bit_and', 'logic_and'): return a[0] & a[1]
        if op in ('bit_or', 'logic_or'): return a[0] | a[1]
        if op in ('bit_xor', 'logic_xor'): return a[0] ^ a[1]
        if op in ('bit_not', 'logic_not'): return ~a[0]
        if op == 'bit_lshift': return u(np.left_shift(i(a[0]), i(a[1]) & 31))
        if op == 'bit_rshift': return u(np.right_shift(i(a[0]), i(a[1]) & 31))
        if op == 'f2i': return u(np.trunc(np.nan_to_num(f(a[0]))).clip(-2**31, 2**31 - 1).astype(np.int32))
        if op == 'i2f': return u(i(a[0]).astype(np.float32))
        if op == 'f2b': return mask(f(a[0]) > 0)
        if op == 'b2f': return u(np.where(a[0] != 0, 1, 0).astype(np.float32))
        if op == 'i2b': return mask(i(a[0]) > 0)
        if op == 'b2i': return u(np.where(a[0] != 0, 1, 0).astype(np.int32))
        raise VMError('kernel %s not implemented' % op)


# ----------------------------------------------------------------------------------------------------------------
# curve data interfaces from their frozen images (VFX0): the LUT the game samples on the CPU

def curve_lut(image, components):
    """(lut float32[samples, components], min time, max time, inv range, samples - 1) of a frozen curve DI image"""
    ptr = struct.unpack_from('<q', image, 24)[0]
    num = struct.unpack_from('<i', image, 32)[0]
    target = 24 + (ptr >> 1)
    lut = np.frombuffer(image[target:target + 4 * num], dtype=np.float32).reshape(-1, components)
    tmin, tmax, inv, nm1 = struct.unpack_from('<ffff', image, 40)
    return lut, tmin, tmax, inv, nm1


def curve_sampler(image, components):
    lut, tmin, tmax, inv, nm1 = curve_lut(image, components)

    def sample(args, n):
        x = args[0]
        r = np.clip((x - tmin) * inv, 0, 1) * nm1
        i0 = np.floor(r).astype(np.int64)
        t = (r - i0).astype(np.float32)
        i1 = np.minimum(i0 + 1, len(lut) - 1)
        i0 = np.minimum(i0, len(lut) - 1)
        v = lut[i0] * (1 - t)[:, None] + lut[i1] * t[:, None]
        return [v[:, k].astype(np.float32) for k in range(components)]
    return sample


CURVE_FUNCTIONS = {'SampleCurve': 1, 'SampleVector2DCurve': 2, 'SampleVectorCurve': 3, 'SampleColorCurve': 4}
