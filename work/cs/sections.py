from dataobj import align
def gather_sections(m, d):
    secs = []
    for r in range(d.rows_num):
        base = d.rows_ptr + r * d.row_size
        for f in d.fields:
            o = base + f['offset']
            if f['kind'] == 'array':
                p, n, mx = m.arr(o)
                if n == 0:
                    assert p is None and mx == 0, (r, f['name'], p, n, mx)
                    continue
                esz = {10: 16, 11: 8, 7: 4, 9: 4, 2: 1}[f['code']]
                if f['code'] == 11:
                    key = ('names', tuple(m.name_at.get(p + i*8) for i in range(n)))
                    secs.append((key, p, n*8, 4, (r, f['name'])))
                elif f['code'] == 10:
                    elems = []; child = []
                    for i in range(n):
                        sp, sn, smx = m.arr(p + i*16)
                        assert sn == smx
                        if sn == 0:
                            assert sp is None; elems.append(None); continue
                        s = m.content[sp:sp+sn*2]
                        elems.append(s)
                        child.append((('str', s), sp, sn*2, 2, (r, f['name'], i)))
                    secs.append((('strarr', tuple(elems)), p, n*16, 8, (r, f['name'])))
                    secs.extend(child)
                else:
                    secs.append((('pod%d' % f['code'], m.content[p:p+n*esz]), p, n*esz, 4, (r, f['name'])))
            elif f['kind'] == 'str':
                sp, sn, smx = m.arr(o)
                assert sn == smx
                if sn == 0:
                    assert sp is None; continue
                secs.append((('str', m.content[sp:sp+sn*2]), sp, sn*2, 2, (r, f['name'])))
    return secs
