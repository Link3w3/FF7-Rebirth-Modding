"""Checks a compiled pixel shader against the carrier shader it replaces: the same input and output signatures, the
same interpolation modes, and (listed, not an error: the new shader has its own resource table) its bindings."""
from . import psinfo
from .dxbc import container, signature


def interp_modes(text):
    """[(semantic, index, mode)] of the dumpbin's input signature interpolation table."""
    out = []
    sec = text.split('; Input signature:\n;\n; Name                 Index             InterpMode DynIdx', 1)
    if len(sec) < 2:
        return out
    for line in sec[1].splitlines()[2:]:
        if line.strip() == ';':
            break
        parts = line[2:].split()
        out.append(tuple(parts[:3]))
    return out


def verify(carrier_info, dxbc):
    """Differences between the carrier's interface and the new shader's (an empty list when they match)."""
    mine = dict(isg=[], osg=[])
    c = container(dxbc, 0)
    for fourcc, o, size in c['parts']:
        if fourcc == 'ISG1':
            mine['isg'] = signature(dxbc, o)
        if fourcc == 'OSG1':
            mine['osg'] = signature(dxbc, o)
    text = psinfo.dump(dxbc)
    problems = []
    if mine['isg'] != carrier_info['isg']:
        problems.append('input signature: %r != %r' % (mine['isg'], carrier_info['isg']))
    if mine['osg'] != carrier_info['osg']:
        problems.append('output signature: %r != %r' % (mine['osg'], carrier_info['osg']))
    a, b = interp_modes(text), interp_modes(carrier_info['text'])
    if a != b:
        problems.append('interpolation: %r != %r' % (a, b))
    carrier_binds = {(x[3]) for x in carrier_info['bindings'] if x[3].startswith(('cb', 't', 's', 'u'))}
    for name, typ, dim, bind in psinfo.bindings(text):
        if bind.startswith(('cb', 't', 's', 'u')) and bind not in carrier_binds:
            problems.append('binding %s (%s) is not one of the carrier\'s' % (bind, name))
    return problems, text
