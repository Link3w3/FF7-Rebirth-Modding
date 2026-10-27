"""Spliced copies of the game's lit translucent shaders, for the checker: the game's own lighting run on the rebuild's
material values. In a copy every material texture is junk (another made-up image) and the material uniform buffer too,
its discard is off, and the material values the lighting takes are read from g_R (the rebuild's outputs) where the
game's material code hands them over. A copy that gives the game's own result therefore had the rebuild supply every
material value the lighting uses, and supply it right.
    splice.py [names...]   ->  gen_s/S_<ns>.cpp, gen_s/index.json   (default: the 14 lit translucent permutations)"""
import json, os, re, sys

H = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(H)
index = json.load(open(os.path.join(H, 'gen/index.json')))
NS = {e['name']: e['ns'] for e in index}
LIT = ['Glass_Thin_Coverage_Wide_Character', 'Crystal_Convex_Wide_Character', 'Crystal_Early_Reverse_Character',
       'Crystal_Thick_Wide_Character', 'Glass_Emissive_Thin_Environment', 'Glass_Thin_Wide_Character',
       'Glass_Thin_Wide_Early_Character', 'Glass_Thin_Wide_Late_Character', 'Water_Thick_Wide_Character',
       'Glass_Emissive_Thin_Wide_Character', 'Glass_Thin_Environment', 'Ocean_Water_Pool_Environment_Development',
       'SoftBody_Water_Pool_Flow_Wide_Detail_Environment_Development', 'Water_Pool_Flow_Wide_Detail_Environment_Development']

# by hand: the ocean's roughness and opacity (worked out from its foam)
MANUAL = {'Ocean_Water_Pool_Environment_Development': {'_754': 'Roughness', '_609': 'Opacity'}}

DEF = re.compile(r'^\s*(?:(?:float|vec[234]|bool|uint|int|uvec[234]|ivec[234]) )?(_\d+) = (.*);\s*$')
TOK = re.compile(r'\b_\d+\b')
SAMPLE = re.compile(r'texture\(sampler2D\((T_\w+),')


class Shader:
    def __init__(self, name):
        self.name = name
        src = open(os.path.join(R, 'named', 'RMI_Surface_%s.glsl' % name)).read()
        lines = src.split('\n')
        start = next(i for i, l in enumerate(lines) if l.startswith('void main()'))
        self.lines = lines[start:]
        self.defs = {}          # name -> [(line index, rhs)]
        for i, l in enumerate(self.lines):
            m = DEF.match(l)
            if m:
                self.defs.setdefault(m.group(1), []).append((i, m.group(2)))
        self.sample = {}        # name -> texture
        for n, ds in self.defs.items():
            for i, rhs in ds:
                m = SAMPLE.search(rhs)
                if m and rhs.startswith('texture('):
                    self.sample[n] = m.group(1)
        self._deps = {}

    def deps(self, name):
        """the material textures (and 'MAT' for the material's parameters) a value is worked out from"""
        if name in self._deps:
            return self._deps[name]
        self._deps[name] = set()
        out = set()
        if name in self.sample:
            out.add(self.sample[name])
        for i, rhs in self.defs.get(name, []):
            out |= self.expr_deps(rhs, skip=name)
        self._deps[name] = out
        return out

    def expr_deps(self, e, skip=None):
        out = set()
        if '{Material_' in e:
            out.add('MAT')
        for m in SAMPLE.finditer(e):
            out.add(m.group(1))
        for t in TOK.findall(e):
            if t != skip:
                out |= self.deps(t)
        return out

    def rhs(self, name):
        ds = self.defs.get(name)
        return ds[0][1] if ds and len(ds) == 1 else None


def balanced_end(s, i):
    """the index just past the parenthesised group that opens at s[i] == '('"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == '(':
            d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0:
                return j + 1
    raise ValueError('unbalanced')


def splice_points(sh):
    """{ssa name: new right-hand side (GLSL/C++ text)}, [(in-expression old, new)], report lines"""
    rep, sub, notes = {}, [], []
    S = 'g_R.'
    # the engine's saturated material values, right after the discard: base colour, metallic, roughness, AO, opacity
    di = next(i for i, l in enumerate(sh.lines) if 'discard_cond(' in l)
    order = {'BaseColor': 0}
    for l in sh.lines[di + 1:di + 40]:
        m = re.match(r'^\s*float (_\d+) = spvNClamp\((.*), 0\.0, 1\.0\);$', l)
        if not m:
            continue
        name, e = m.group(1), m.group(2)
        d = sh.expr_deps(e)
        attr = None
        if 'T_Color' in d:
            attr = 'BaseColor.' + 'xyz'[order['BaseColor']]
            order['BaseColor'] += 1
        elif 'T_Metallic' in d:
            attr = 'Metallic'
        elif d & {'T_Roughness'}:
            attr = 'Roughness'
        elif d & {'T_Occlusion', 'T_WideOcclusion'}:
            attr = 'AO'
        elif 'T_Opacity' in d:
            attr = 'Opacity'
        if attr:
            rep[name] = 'spvNClamp(%s%s, 0.0, 1.0)' % (S, attr)
            notes.append('%s = saturate(%s)   [was %s; from %s]' % (name, attr, e[:60], ','.join(sorted(d))))
    # the ones the rules above can't tell (the material's own values, from no texture of their own)
    for n, a in MANUAL.get(sh.name, {}).items():
        rep[n] = 'spvNClamp(%s%s, 0.0, 1.0)' % (S, a)
        notes.append('%s = saturate(%s)   [by hand; was %s]' % (n, a, (sh.rhs(n) or '')[:60]))
    # the same saturated values where the lighting clamps a raw texture read in place (no separate value for it)
    attr_of = {'T_Color': 'BaseColor', 'T_Metallic': 'Metallic', 'T_Roughness': 'Roughness', 'T_Occlusion': 'AO', 'T_Opacity': 'Opacity'}
    for n, t in sh.sample.items():
        if t in attr_of:
            for c in ('xyz' if t == 'T_Color' else 'x'):
                a = attr_of[t] + ('.' + c if t == 'T_Color' else '')
                pat = 'spvNClamp(%s.%s, 0.0, 1.0)' % (n, c)
                sub.append((pat, 'spvNClamp(%s%s, 0.0, 1.0)' % (S, a), 'any'))
    # the tangent-space normal, where the material template normalizes it before taking it to world space
    for l in sh.lines:
        m = re.search(r'fma\((_\d+), TEXCOORD_11\.x, fma\((_\d+), (?:\(\(TEXCOORD_10\.z \* TEXCOORD_11\.y\) - \(TEXCOORD_10\.y \* '
                      r'TEXCOORD_11\.z\)\) \* TEXCOORD_11\.w|_\d+), (_\d+) \* TEXCOORD_10\.x\)\)', l)
        if m:
            n3, n2, n1 = m.groups()
            parts = []
            for n in (n1, n2, n3):
                mm = re.fullmatch(r'(_\d+) \* (_\d+)', sh.rhs(n) or '')
                parts.append(mm.groups() if mm else None)
            if all(parts) and len({p[0] for p in parts}) == 1:
                r, abc = parts[0][0], [p[1] for p in parts]
                if sh.deps(abc[0]) or sh.deps(abc[1]) or sh.deps(abc[2]):
                    v = 'vec3(%sNormal.x, %sNormal.y, %sNormal.z)' % (S, S, S)
                    rep[r] = 'inversesqrt(dot(%s, %s))' % (v, v)
                    for n, c in zip((n1, n2, n3), 'xyz'):
                        rep[n] = '%s * %sNormal.%s' % (r, S, c)
                    notes.append('normal: %s,%s,%s (1/len %s) [was %s]' % (n1, n2, n3, r, ','.join(abc)))
            break
    # the medium inside: muddiness, transparency and transmittance (log2 per unit length), thickness
    for n, t in sh.sample.items():
        if t == 'T_Muddiness':
            rep[n] = 'vec4(%sMuddiness.x, %sMuddiness.y, %sMuddiness.z, 0.0)' % (S, S, S)
            notes.append('%s = Muddiness' % n)
        if t in ('T_Thinness', 'T_Thickness'):
            rep[n] = 'vec4(%sThickness)' % S
            notes.append('%s = Thickness (%s)' % (n, t))
    tr = [n for n, t in sh.sample.items() if t == 'T_Transparency']
    tm = [n for n, t in sh.sample.items() if t == 'T_Transmittance']
    for n, ds in sh.defs.items():
        if len(ds) != 1:
            continue
        rhs = ds[0][1]
        for t in tr:
            if re.match(r'log2\(spvNClamp\(%s\.x, 0\.0, 1\.0\)\) \* ' % t, rhs):
                rep[n] = S + 'TransparencyLog2'
                notes.append('%s = TransparencyLog2' % n)
        for t in tm:
            m = re.match(r'log2\(spvNClamp\(%s\.([xyz]), 0\.0, 1\.0\)\) \* ' % t, rhs)
            if m:
                rep[n] = S + 'TransmittanceLog2.' + m.group(1)
                notes.append('%s = TransmittanceLog2.%s' % (n, m.group(1)))
    # foam on water, where the lighting fades it in with depth: saturate(depth / 50) * saturate(the material's foam)
    for l in sh.lines:
        k = l.find('spvNClamp(')
        while k >= 0:
            m = re.match(r'spvNClamp\(_\d+ \* 0\.0199999995529651641845703125, 0\.0, 1\.0\) \* spvNClamp\(', l[k:])
            if m:
                a = k + m.end() - len('spvNClamp(')
                b = balanced_end(l, a + len('spvNClamp'))
                g = l[a:b]
                if sh.expr_deps(g) & {'T_Foam', 'T_DetailFoam', 'T_OceanGeometry', 'MAT'}:
                    sub.append((g, S + 'Foam', 'one'))
                    notes.append('foam: %s' % g[:70])
            k = l.find('spvNClamp(', k + 1)
    # emissive, where the lighting adds it: max(0, the material's emissive)
    em = [n for n, t in sh.sample.items() if t == 'T_Emissive']
    for e in em:
        for l in sh.lines:
            k = 0
            while True:
                k = l.find('spvNMax(0.0, ', k)
                if k < 0:
                    break
                a = k + len('spvNMax(0.0, ')
                b = balanced_end(l, k + len('spvNMax')) - 1
                inner = l[a:b]
                m = re.search(r'\b%s\.([xyz])\b' % e, inner)
                if m:
                    sub.append((inner, S + 'Emissive.' + m.group(1), 'one'))
                    notes.append('emissive.%s: %s' % (m.group(1), inner[:80]))
                k = b
    return rep, sub, notes


def glsl_to_cpp(e):
    """a GLSL expression as the transpiled C++ writes it (the {annotations} back to buffer reads)"""
    return e


def make(name):
    ns = NS['RMI_Surface_' + name]
    sh = Shader(name)
    rep, sub, notes = splice_points(sh)
    cpp = open(os.path.join(H, 'gen', ns + '.cpp')).read().split('\n')
    done = set()
    out = []
    for l in cpp:
        m = re.match(r'^(\s*(?:\w+ )?)(_\d+) = (.*);\s*$', l)
        if m and m.group(2) in rep and l.startswith('    '):
            l = '%s%s = %s;' % (m.group(1), m.group(2), rep[m.group(2)])
            done.add(m.group(2))
        if re.match(r'^\s+discard_cond\(', l):
            l = l.replace('discard_cond(', '(void)(', 1)
        l = re.sub(r'texid\("(T_\w+)"\)', r'texid("junk:\1")', l)
        m = re.match(r'^static (UBO\w*)& (Material\w*) = (\w+)\("(\w+)"\);$', l)
        if m:
            l = 'static %s& %s = %s("junk:%s");' % m.groups()
        out.append(l)
    text = '\n'.join(out)
    # the in-expression ones, in the C++ text (its buffer reads differ from the annotated GLSL)
    for old, new, how in sub:
        cold = re.sub(r'\{Material_V(\d+)\.([xyzw])=[^}]*\}', r'Material._m0[\1u].\2', old)
        cold = re.sub(r'\{View_OneOverPreExposure\}', 'View._m0[164u].z', cold)
        n = text.count(cold)
        if how == 'one' and n != 1:
            raise SystemExit('%s: pattern found %d times: %s' % (name, n, cold))
        if n:
            notes.append('in place (%d): %s -> %s' % (n, cold[:50], new))
        text = text.replace(cold, new)
    missing = set(rep) - done
    if missing:
        raise SystemExit('%s: not found in the C++: %s' % (name, sorted(missing)))
    text = text.replace('namespace %s {' % ns, 'namespace S%s {' % ns[1:], 1).replace('} // namespace %s' % ns, '} // namespace S%s' % ns[1:])
    os.makedirs(os.path.join(H, 'gen_s'), exist_ok=True)
    open(os.path.join(H, 'gen_s', 'S%s.cpp' % ns[1:]), 'w').write(text)
    return ns, notes


if __name__ == '__main__':
    names = sys.argv[1:] or LIT
    idx = []
    for n in names:
        ns, notes = make(n)
        idx.append({'name': 'RMI_Surface_' + n, 'ns': 'S' + ns[1:]})
        print('== %s' % n)
        for x in notes:
            print('   ' + x)
    p = os.path.join(H, 'gen_s', 'index.json')
    old = json.load(open(p)) if os.path.exists(p) else []
    keep = [e for e in old if e['name'] not in {i['name'] for i in idx}]
    json.dump(keep + idx, open(p, 'w'), indent=1)
