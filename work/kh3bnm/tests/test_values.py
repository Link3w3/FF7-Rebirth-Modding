"""Every value of the KH3 file (read by the independent tagged.py reader) against the converter's v2 data."""
import json, re, struct, sys
raw = json.load(open('/work/kh3bnm/test/p_ex011_raw.json'))
spec = json.load(open('/work/kh3bnm/test/p_ex011_v2.json'))
f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
fails, checked = [], [0]

def v2_enum(s):
    for a, b in (('CollisionShape_', 'CollisionShape_v2_'), ('ConstraintType_', 'ConstraintType_v2_'), ('LinkType_', 'LinkType_v2_'),
                 ('FMH_', 'FMH_v2_'), ('JOINTLINK_MODE_', 'JOINTLINK_MODE_v2_'), ('PSSMODE_', 'PSSMODE_v2_')):
        if a in s and b not in s: return s.replace(a, b)
    return s

def same(a, b, where):
    checked[0] += 1
    if isinstance(a, dict):
        keys = [k for k in a if k != '__order__']
        base = {}
        for k in keys:
            m = re.match(r'^(.*)\[(\d+)\]$', k)
            name, idx = (m.group(1), int(m.group(2))) if m else (k, 0)
            base.setdefault(name, {})[idx] = a[k]
        for name, elems in base.items():
            if name == 'm_FpsCorrection':
                if any(elems.values()): fails.append(where + ': non-empty fps correction')
                if name in b: fails.append(where + ': fps correction kept')
                continue
            if name not in b: fails.append('%s.%s missing' % (where, name)); continue
            if isinstance(b[name], list) and (len(elems) > 1 or (not isinstance(elems[0], list) and isinstance(b[name], list))):
                for i, v in elems.items(): same(v, b[name][i], '%s.%s[%d]' % (where, name, i))
                # unstored elements must be zero
                for i in range(len(b[name])):
                    if i not in elems and b[name][i] not in (0, 0.0, '', False): fails.append('%s.%s[%d] not zero' % (where, name, i))
            else:
                same(elems[0], b[name], '%s.%s' % (where, name))
        extra = [k for k in b if k not in base]
        if extra: fails.append('%s: extra %s' % (where, extra))
        return
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b): fails.append('%s: %r vs %r' % (where, a, b)); return
        for i, (x, y) in enumerate(zip(a, b)): same(x, y, '%s[%d]' % (where, i))
        return
    if isinstance(a, float):
        if not isinstance(b, float) or f32(a) != f32(b) or (str(a).startswith('-') != str(b).startswith('-')): fails.append('%s: %r vs %r' % (where, a, b))
        return
    if isinstance(a, str) and a.startswith('ESQEX_'):
        if v2_enum(a) != b: fails.append('%s: %r vs %r' % (where, a, b))
        return
    if a != b or type(a) != type(b): fails.append('%s: %r vs %r' % (where, a, b))

same(raw, spec, 'v2')
print('checked %d values; %d differences' % (checked[0], len(fails)))
for f in fails[:20]: print('  ', f)
sys.exit(1 if fails else 0)
