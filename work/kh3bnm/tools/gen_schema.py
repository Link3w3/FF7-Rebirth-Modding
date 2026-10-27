"""Prints the Bonamik v2 schema (field order, kinds) and the enum tables for embedding in kh3bonamik.py."""
import os, re, sys
sys.path.insert(0, '/work/bnm/tools')
from schema import parse_headers
PUB = '/work/bnm/Plugins/BonamikPlugin/Source/BonamikRt/Public'
S, E = parse_headers()

def kind(t):
    t = t.strip()
    simple = {'uint32': 'u32', 'int32': 'i32', 'bool': 'bool', 'float': 'f32', 'FString': 'str', 'FName': 'name',
              'FVector': 'vec', 'FQuat': 'quat', 'uint8': 'u8'}
    if t in simple: return repr(simple[t])
    m = re.match(r'TEnumAsByte<(\w+)>', t)
    if m: return repr(('enum', m.group(1)))
    m = re.match(r'TArray<(.+)>$', t)
    if m: return "('array', %s)" % kind(m.group(1))
    if t.endswith('*'): return repr('object')
    if t.startswith('F') and t in S: return repr(('struct', t[1:]))
    raise ValueError(t)

types = ['USQEX_BonamikAsset_v2', 'FSQEX_BonamikSceneManagerDesc_v2', 'FSQEX_BonamikSolverDesc_v2', 'FSQEX_BonamikBodyDesc_v2',
         'FSQEX_BonamikLinkDesc_v2', 'FSQEX_BonamikPlaneDesc_v2', 'FSQEX_BonamikShapeMatchingDesc_v2',
         'FSQEX_BonamikPossessionDesc_v2', 'FSQEX_BonamikGroupLOD_v2']
print('V2_TYPES = {')
for t in types:
    name = t[1:]
    print('    %r: [' % name)
    for p, pt, dim in S[t]['props']:
        k = kind(pt)
        print('        (%r, %s, %d),' % (p, k, dim))
    print('    ],')
print('}')

def entries(enum):
    for f in os.listdir(PUB):
        if f == enum + '.h':
            text = open(os.path.join(PUB, f)).read()
            m = re.search(r'enum\s+(?:class\s+)?(\w+)\s*(?::\s*\w+)?\s*{([^}]*)}', text)
            out = []
            for e in m.group(2).split(','):
                e = e.strip()
                if not e: continue
                assert '=' not in e, e
                out.append(e)
            return out
    raise KeyError(enum)

enums = sorted(set(re.findall(r"'enum', '(\w+)'", open(__file__).read())) | set())
used = set()
for t in types:
    for p, pt, dim in S[t]['props']:
        m = re.search(r'TEnumAsByte<(\w+)>', pt)
        if m: used.add(m.group(1))
print('V2_ENUMS = {')
for e in sorted(used):
    print('    %r: %r,' % (e, entries(e)))
print('}')
print('KH3_ENUMS = {  # the 2.x enums under their KH3 names (same entries in the same order)')
for e in sorted(used):
    old = e.replace('_v2', '')
    print('    %r: %r,' % (old, entries(old)))
print('}')
