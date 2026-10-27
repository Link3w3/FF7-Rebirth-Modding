"""HSFLipMap (HSF lip sync's lip map) reading: the usmap parser with the attribute enum read as the FName the game stores."""
import sys
sys.path[:0] = ['/work/fx1018/editor/Python', '/work/iostore', '/work/cs']
from rebirth_fx import uprops
from rebirth_fx.fxcore import Package

_orig = uprops.Reader.value


def _value(self, pt):
    if pt.type == 'EnumProperty' and getattr(pt, 'enum', None) == 'EHSFLipMapShapeAttributeType':
        at = self.p
        nm = self.name()
        return uprops.V('enum', pt.enum, at, self.p - at, nm)
    return _orig(self, pt)


uprops.Reader.value = _value


def plain(v):
    if v.kind == 'struct':
        return {k: plain(x) for k, x in v.value.items()}
    if v.kind in ('array', 'set'):
        return [plain(x) for x in v.value]
    if v.kind == 'map':
        return [(plain(a), plain(b)) for a, b in v.value]
    return v.value


def read(path_or_data, label=''):
    d = open(path_or_data, 'rb').read() if isinstance(path_or_data, str) else path_or_data
    p = Package(d, label or str(path_or_data))
    assert not p.errors, p.errors
    (cls, v, base), = p.exports.values()
    return p, cls, v


if __name__ == '__main__':
    p, cls, v = read(sys.argv[1])
    d = {k: plain(x) for k, x in v.value.items()}
    print(cls, list(d))
    print('Version', d.get('Version'))
    for shape, s in d.get('Shapes', []):
        attrs = s.get('Attributes', [])
        print('shape %-5s %s' % (shape, {k: s[k] for k in s if k != 'Attributes'}))
        for bone, a in attrs:
            print('      %-14s %s' % (bone, ', '.join('%s=%.3f' % (str(k).split('::')[-1], val) for k, val in a['Data'])))
    for k in ('DefaultShape', 'MaxDifferenceShape'):
        s = d.get(k)
        if s:
            print(k, {kk: s[kk] for kk in s if kk != 'Attributes'})
            for bone, a in s.get('Attributes', []):
                print('      %-14s %s' % (bone, ', '.join('%s=%.3f' % (str(kk).split('::')[-1], val) for kk, val in a['Data'])))
