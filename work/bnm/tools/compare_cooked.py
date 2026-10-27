"""Checks a cooked PC0011_10_BNM (from the editor script's RebirthAssetLibrary cook) against the script's spec and
against the layout of the game's own PC0010_10_BNM.
    python3 compare_cooked.py <cooked .uasset> [script .py]"""
import importlib.util, sys
import numpy as np
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/bnm/tools')
from legacy import Legacy
from tagged import Reader, read_props
from load import load

path = sys.argv[1]
script = sys.argv[2] if len(sys.argv) > 2 else '/work/bnm/ChaosVincentBonamik/make_chaos_vincent_wing_bonamik.py'
s_ = importlib.util.spec_from_file_location('chaos_bnm', script); M = importlib.util.module_from_spec(s_); s_.loader.exec_module(M)
uexp = path[:-len('.uasset')] + '.uexp'
try:
    ue = open(uexp, 'rb').read()
except FileNotFoundError:
    ue = b''
L = Legacy(open(path, 'rb').read(), ue)
print('package flags %08x  ue4ver %d  names %d  imports %d  exports %d' % (L.flags, L.ue4ver, len(L.names), len(L.imports), len(L.exports)))
def ref(i):
    if i < 0: return 'import:' + L.imports[-i - 1][3]
    if i > 0: return 'export:' + L.exports[i - 1]['name']
    return 'null'
for i, e in enumerate(L.exports):
    print('  export %d %-26s class %-32s outer %-22s flags %08x size %d' % (i + 1, e['name'], ref(e['cls']), ref(e['outer']), e['flags'], e['size']))
objs = [read_props(Reader(L.export_data(i), L.names)) for i in range(len(L.exports))]

SL, sobjs = load('PC0010_10_Sephiroth_Transform/Model/PC0010_10_BNM')
print('Sephiroth for comparison:')
for i, e in enumerate(SL.exports):
    print('  export %d %-26s outer %d flags %08x' % (i + 1, e['name'], e['outer'], e['flags']))

fails = []
def check(ok, what):
    if not ok: fails.append(what)
w = next(o for o, e in zip(objs, L.exports) if ref(e['cls']).endswith('SQEX_BonamikAsset'))
v = next(o for o, e in zip(objs, L.exports) if ref(e['cls']).endswith('SQEX_BonamikAsset_v2'))
ve = next(e for e in L.exports if ref(e['cls']).endswith('SQEX_BonamikAsset_v2'))
check(w.get('m_VersionNo') == 2401, 'wrapper m_VersionNo %r' % w.get('m_VersionNo'))
check(isinstance(w.get('v2'), tuple) and ref(w['v2'][1]) == 'export:' + ve['name'], 'wrapper v2 -> %r' % (w.get('v2'),))
check(ref(ve['outer']).startswith('export:') and ve['name'] == 'SQEX_BonamikAsset_v2_0', 'v2 export name/outer')
check(set(w['__order__']) == set(sobjs[0]['__order__']), 'wrapper fields %s vs Sephiroth %s' % (w['__order__'], sobjs[0]['__order__']))

spec = M.build_spec()
f32 = np.float32
def same(exp, got, where):
    if isinstance(exp, M.Enum):
        check(got == exp.entry, '%s: %r vs %r' % (where, got, exp.entry)); return
    if isinstance(exp, (list, tuple)) and not isinstance(exp, str):
        if isinstance(got, list) and len(got) == len(exp):
            for k, (a, b) in enumerate(zip(exp, got)): same(a, b, '%s[%d]' % (where, k))
        else: check(False, '%s: %r vs %r' % (where, got, exp))
        return
    if isinstance(exp, float):
        check(isinstance(got, float) and f32(got) == f32(exp), '%s: %r vs %r' % (where, got, exp)); return
    check(got == exp, '%s: %r vs %r' % (where, got, exp))

def fixed(d, name, n):
    return [d.get(name if i == 0 else '%s[%d]' % (name, i), 0) for i in range(n)]

# top level: present = differs from defaults
for k, val in spec.items():
    if isinstance(val, (dict, list)): continue
    default = 0
    if val == default: check(k not in v, 'v2 %s written though default' % k)
    else: same(val, v.get(k), 'v2.' + k)
# scene
sm = v['m_SceneManager']; sp = spec['m_SceneManager']
for k, val in sp.items():
    if isinstance(val, list):
        same(val, fixed(sm, k, len(val)), 'scene.' + k); continue
    if k in sm: same(val, sm[k], 'scene.' + k)
    else: check(val in (0, 0.0, False, '') , 'scene.%s missing (value %r)' % (k, val))
extra = [k for k in sm['__order__'] if k.split('[')[0] not in sp]
check(not extra, 'scene has fields the spec does not set: %s' % extra)
ssm = sobjs[1]['m_SceneManager']
check(set(k.split('[')[0] for k in sm['__order__']) <= set(k.split('[')[0] for k in ssm['__order__']), 'scene fields beyond Sephiroth\'s')
# arrays: every element fully written
for key in ('m_Solvers', 'm_Bodies', 'm_Links'):
    got = v.get(key, []); exp = spec[key]
    check(len(got) == len(exp), '%s: %d entries vs %d' % (key, len(got), len(exp)))
    seph_fields = sobjs[1][key][0]['__order__']
    for i, (g, e) in enumerate(zip(got, exp)):
        check(g['__order__'] == seph_fields, '%s[%d] field order differs from Sephiroth' % (key, i))
        for k, val in e.items():
            if k == 'm_ColId': same(val, fixed(g, 'm_ColId', 8), '%s[%d].m_ColId' % (key, i))
            else: same(val, g.get(k), '%s[%d].%s' % (key, i, k))
check('m_Planes' not in v and 'm_ShapeMatchings' not in v, 'planes / shape matchings written')
print('bodies %d links %d solvers %d' % (len(v.get('m_Bodies', [])), len(v.get('m_Links', [])), len(v.get('m_Solvers', []))))
print('FAILS:' if fails else 'COOKED FILE MATCHES THE SPEC AND SEPHIROTH\'S LAYOUT', fails[:30])
