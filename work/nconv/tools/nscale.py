"""Scale a particle attribute's stored value (sprite size, mesh scale) by k in a converted emitter's scripts.

KH3's effects were authored in Cascade, which multiplies sprite sizes (and mesh sizes) by the owning component's scale;
some of the KH3 summon's emitters were made for a 100x scaled keyblade bone and come out of the End editor's Cascade to
Niagara conversion with sizes 1/100 of what they looked like in KH3. Niagara does not scale sprite sizes by the component
(the game's neither), so the size is scaled in the data itself: every write of the attribute's components stores
value * k, and every read divides by k again, so the scripts' own arithmetic (curves over the initial size, growth from
the last frame's size) still runs in KH3's units and only the renderers see the scaled value.

    write:  outputdata_float ds0 idx src comp   ->   mul t = src * k;  outputdata_float ds0 idx t comp
    read:   inputdata_float  ds0 comp -> d      ->   inputdata_float ...;  mul d = d * (1/k)
t is one new temporary register (the script's NumTempRegisters + 1).
"""
import struct
import nvvm


class Scaler:
    def __init__(self, components, k):
        """components: data set 0 float component indices to scale (in the final particle layout)"""
        self.components = set(components)
        self.k = float(k)

    def transform(self, code, ext_counts, literal_base, literals, num_temp):
        """-> (code, literals, num_temp)"""
        lits = bytearray(literals)
        const_at = {}

        def const(value):
            v = struct.unpack('<f', struct.pack('<f', value))[0]
            if v not in const_at:
                const_at[v] = literal_base + len(lits)
                lits.extend(struct.pack('<f', v))
            return const_at[v]

        t = num_temp                         # the new temporary register
        mul = nvvm.OP['mul']
        out = bytearray()
        writes = reads = 0
        for x in nvvm.decode(code, ext_counts):
            body = bytearray(code[x.at:x.at + x.size])
            if x.op in ('inputdata_float', 'inputdata_noadvance_float'):
                ds, comp, dest = x.operands[0][2], x.operands[1][2], x.operands[2][2]
                out += body
                if ds == 0 and comp in self.components:
                    # d = d * (1/k): src0 register, src1 constant (types bit 1)
                    out += struct.pack('<BBHHH', mul, 2, dest, const(1.0 / self.k), dest)
                    reads += 1
                continue
            if x.op == 'outputdata_float':
                ds, comp = x.operands[0][2], x.operands[3][2]
                if ds == 0 and comp in self.components:
                    sk, spos, sv = x.operands[2]
                    # t = src * k (src a register: types 2; a constant: types 3)
                    out += struct.pack('<BBHHH', mul, 3 if sk == 'c' else 2, sv, const(self.k), t)
                    body[1] = x.types & ~1           # the output's source is now a register
                    struct.pack_into('<H', body, spos - x.at, t)
                    writes += 1
                out += body
                continue
            out += body
        back = nvvm.decode(bytes(out), ext_counts)
        assert back[-1].op == 'done'
        self.last = {'writes': writes, 'reads': reads}
        if not writes and not reads:
            return code, literals, num_temp          # (the script does not touch the attribute)
        return bytes(out), bytes(lits), num_temp + 1
