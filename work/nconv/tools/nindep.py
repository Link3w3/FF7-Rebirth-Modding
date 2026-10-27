"""SQEX per-particle material parameters for converted sprite and mesh emitters.

The game's particle materials (RMI_Particle_*) read their colour, coverage and so on from five Vector4 particle
attributes that SE's module FX_Gen_Sprite_0_SetParticleMaterialParameter writes, bound by the sprite renderer's
VfxMaterialIndependentParameters0..7 bindings; the game's sprite emitters have no Particles.Color at all. A converted
KH3 emitter has Particles.Color but none of these, so this adds them: the attributes go into the particle data set
(sorted in, as the game's are: case-insensitive name order), the scripts' data set component operands are moved to the
new layout, and after each script's Color outputs the same values are written again as the material parameters.

Values, as the game's own Hit_01 smoke writes them (nsim.py on FX_PC0000_BurstChain00_01_Hit_01):
  IndependentParameter0 = (seed, 1, id, 0)       -> written as (0, 1, 0, 0)
  IndependentParameter1 = (r, g, b, alpha)        -> Particles.Color
  IndependentParameter2 = (1, 1, 1, 0)            -> (Color.rgb, 0)
  IndependentParameter4 = (x, 0, 0, 0), x rising  -> (0, 0, 0, 0)
  IndependentParameter5 = (1, 0, 0, 0)            -> (1, 0, 0, 0)
"""
import struct
import nvvm

PREFIX = 'FX_Gen_Sprite_0_SetParticleMaterialParameter.IndependentParameter'
MESH_PREFIX = 'FX_Gen_Mesh_0_SetParticleMaterialParameter.IndependentParameter'   # (the same module for mesh renderers)
VEC4 = (0x61a8c652, 2)
COLOR = 0xe2a7510c
PARAMS = (0, 1, 2, 4, 5)
# per parameter, per component: ('color', k) or ('const', value)
VALUES = {
    0: [('const', 0.0), ('const', 1.0), ('const', 0.0), ('const', 0.0)],
    1: [('color', 0), ('color', 1), ('color', 2), ('color', 3)],
    2: [('color', 0), ('color', 1), ('color', 2), ('const', 0.0)],
    4: [('const', 0.0), ('const', 0.0), ('const', 0.0), ('const', 0.0)],
    5: [('const', 1.0), ('const', 0.0), ('const', 0.0), ('const', 0.0)],
}
NO_COLOR = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0}      # an emitter without Particles.Color: white, opaque


def float_components(vars_, layouts):
    """{name: [float component indices]} for a list of (name, (type hash, utype))"""
    out, at = {}, 0
    for nm, th in vars_:
        fl = layouts[th[0]][0]
        out[nm] = list(range(at, at + len(fl)))
        at += len(fl)
    return out, at


class Plan:
    """the new particle data set of one emitter and how its float components move"""

    def __init__(self, vars_, layouts, prefixes=(PREFIX,)):
        """prefixes: one set of the five attributes per renderer kind the emitter has (sprite, mesh)"""
        self.old_vars = list(vars_)
        self.prefixes = list(prefixes)
        names = {nm for nm, th in vars_}
        added = [(pf + str(k), VEC4) for pf in self.prefixes for k in PARAMS if pf + str(k) not in names]
        if len(added) != len(PARAMS) * len(self.prefixes):
            raise ValueError('the emitter already has some of the material parameters')
        self.new_vars = sorted(self.old_vars + added, key=lambda t: t[0].lower())
        old, self.old_total = float_components(self.old_vars, layouts)
        new, self.new_total = float_components(self.new_vars, layouts)
        self.remap = {}
        for nm, comps in old.items():
            for a, b in zip(comps, new[nm]):
                self.remap[a] = b
        self.params = [{k: new[pf + str(k)] for k in PARAMS} for pf in self.prefixes]
        color = [nm for nm, th in self.old_vars if nm == 'Color' and th[0] == COLOR]
        self.color = old['Color'] if color else None          # old component indices of Particles.Color

    def transform(self, code, ext_counts, literal_base, literals):
        """the script's byte code with data set 0's float components moved and the material parameters written after
        its Color outputs; -> (code, literals). literal_base: where the literal table starts in the constant table
        (the game's layout), literals: the script's literal bytes (two floats, 0 and 1, are added as needed)."""
        lits = bytearray(literals)
        const_at = {}

        def const(value):
            if value not in const_at:
                const_at[value] = literal_base + len(lits)
                lits.extend(struct.pack('<f', value))
            return const_at[value]

        ins = nvvm.decode(code, ext_counts)
        out = bytearray()
        prev = 0
        color_written = set()
        anchor = None              # an output's (index register) after which the constant parameters go
        constants_done = False

        def emit(index_reg, kind, value, comp):
            if kind == 'reg':
                return struct.pack('<BBHHHH', nvvm.OP['outputdata_float'], 0, 0, index_reg, value, comp)
            return struct.pack('<BBHHHH', nvvm.OP['outputdata_float'], 1, 0, index_reg, const(value), comp)

        for x in ins:
            body = bytearray(code[x.at:x.at + x.size])
            extra = bytearray()
            if x.op in ('inputdata_float', 'inputdata_noadvance_float'):
                ds, comp = x.operands[0][2], x.operands[1][2]
                if ds == 0:
                    struct.pack_into('<H', body, x.operands[1][1] - x.at, self.remap[comp])
            elif x.op == 'outputdata_float':
                ds, ireg, (sk, sp, sv), comp = x.operands[0][2], x.operands[1][2], x.operands[2], x.operands[3][2]
                if ds == 0:
                    struct.pack_into('<H', body, x.operands[3][1] - x.at, self.remap[comp])
                    if anchor is None:
                        anchor = ireg
                        if self.color is None:   # no colour: white and opaque, right after the first output
                            for p in PARAMS:
                                for c, (kind, v) in enumerate(VALUES[p]):
                                    if kind == 'color':
                                        for ps in self.params:
                                            extra += emit(ireg, 'const', NO_COLOR[v], ps[p][c])
                            extra += self._constants(ireg, emit)
                            constants_done = True
                    if self.color is not None and comp in self.color:
                        k = self.color.index(comp)
                        color_written.add(k)
                        for p in PARAMS:
                            for c, (kind, v) in enumerate(VALUES[p]):
                                if kind == 'color' and v == k:
                                    for ps in self.params:
                                        if sk == 'c':    # a constant colour component: the same constant
                                            extra += struct.pack('<BBHHHH', nvvm.OP['outputdata_float'], 1, 0, ireg, sv,
                                                                 ps[p][c])
                                        else:
                                            extra += emit(ireg, 'reg', sv, ps[p][c])
                        if k == 3 and not constants_done:
                            extra += self._constants(ireg, emit)
                            constants_done = True
            elif x.op == 'done':
                if not constants_done:
                    raise ValueError('the script writes no particle attribute' if anchor is None else
                                     'the script never writes Color.a')
            out += body + extra
        if self.color is not None and color_written != {0, 1, 2, 3}:
            raise ValueError('the script writes Color components %s only' % sorted(color_written))
        back = nvvm.decode(bytes(out), ext_counts)          # (it still decodes)
        assert back[-1].op == 'done'
        return bytes(out), bytes(lits)

    def _constants(self, ireg, emit):
        b = bytearray()
        for ps in self.params:
            for p in PARAMS:
                for c, (kind, v) in enumerate(VALUES[p]):
                    if kind == 'const':
                        b += emit(ireg, 'const', v, ps[p][c])
        return b
