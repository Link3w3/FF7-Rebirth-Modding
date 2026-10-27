"""Offline check of the DLL's TableCopies and Characters::Edit (3.16.0) on the real tables: each table's frozen image is
put in a simulated address space as the game has it (relative pointers, FNames patched in), the C++ steps are done the
same way (a copy of the root and the rows in far-away memory, every frozen pointer made again for its new place, the
character's edits of CloudCharacter.json), then the copy is read back from its root alone (as the game's readers would)
and compared, field by field, with what it must be:
  * every row the edits do not name: the game's row as it was;
  * names: Cloud's CharaSpec rows mapped (PlayerTable, PlannerEventChara, BikeCharaSpec, Equipment);
  * rows: pt_Cloud as pt_Cloud_CACS (= the game's own pt_Cloud), the 11 abilities as their _CACS rows but the UniqueId;
  * values: PlannerEvent's VoicePack, PlannerEventVoiceList's texts, Equipment W_TSW_9001.
    sim_tablecopies.py <CloudCharacter.json> <FPYS data build dir (tables/)>"""
import json, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/charaspecmod']
import charaspec_patch as cp

GX = '/work/owncloud/gx/'
NAMES = {}      # text -> comparison index (the simulated name table)
TEXT = {0: None}


def name_id(text):
    if text is None:
        return 0
    if text not in NAMES:
        NAMES[text] = len(NAMES) + 1
        TEXT[NAMES[text]] = text
    return NAMES[text]


def raw(text):
    """A simulated FName {comparison, number}: the text is the comparison (number 0)."""
    return struct.pack('<II', name_id(text), 0)


def text_of(b):
    c, n = struct.unpack('<II', b)
    return TEXT[c] if n == 0 else '%s_%d' % (TEXT[c], n - 1)


class Mem:
    def __init__(self):
        self.regions = []

    def add(self, base, data):
        self.regions.append((base, bytearray(data)))
        return base

    def at(self, addr, n):
        for base, buf in self.regions:
            if base <= addr and addr + n <= base + len(buf):
                return buf, addr - base
        raise IndexError(hex(addr))

    def read(self, addr, n):
        buf, o = self.at(addr, n)
        return bytes(buf[o:o + n])

    def write(self, addr, b):
        buf, o = self.at(addr, len(b))
        buf[o:o + len(b)] = b

    def i64(self, a): return struct.unpack('<q', self.read(a, 8))[0]
    def i32(self, a): return struct.unpack('<i', self.read(a, 4))[0]
    def put64(self, a, v): self.write(a, struct.pack('<q', v))
    def put32(self, a, v): self.write(a, struct.pack('<i', v))


M = Mem()
NEXT = [0x0000020000000000]


def alloc(n, align=16):
    base = (NEXT[0] + align - 1) & ~(align - 1)
    NEXT[0] = base + n + 0x1000
    return M.add(base, bytes(n))


def resolve(at, value):
    if value == 0:
        return 0
    if value & 1:
        return at + (value >> 1)
    return value


def encode(at, target):
    return (target - at) * 2 + 1


def moved(frm, to, value):
    return 0 if value == 0 else encode(to, resolve(frm, value))


# ---- the table layout (SkelCompat::Frozen::Layout) ----
SIZE = {1: (1, 1), 2: (1, 1), 3: (1, 1), 4: (2, 2), 5: (2, 2), 6: (4, 4), 7: (4, 4), 8: (8, 8), 9: (4, 4), 10: (16, 8), 11: (8, 4)}


def layout(fields):
    off, ra, out = 0, 1, []
    for name, code in fields:
        arr = name.endswith('_Array')
        size, al = (16, 8) if arr else SIZE[code]
        off = (off + al - 1) // al * al
        out.append(dict(Name=name, Type=code, Array=arr, Offset=off, Size=size))
        off += size
        ra = max(ra, al)
    return out, (off + ra - 1) // ra * ra


class Table:
    """OpenTableAt: the table whose frozen root is at `root` (elements copied, fields, rows address)."""
    def __init__(self, root):
        self.root = root
        el = resolve(root, M.i64(root)); self.count = M.i32(root + 8)
        sd = resolve(root + 56, M.i64(root + 56)); nf = M.i32(root + 64)
        self.rows = resolve(root + 72, M.i64(root + 72)); nr = M.i32(root + 80)
        assert nr == self.count
        defs = [(text_of(M.read(sd + 12 * k, 8)), M.i32(sd + 12 * k + 8)) for k in range(nf)]
        self.fields, self.row_size = layout(defs)
        self.keys = {}
        for k in range(self.count):
            key = text_of(M.read(el + 20 * k, 8))
            self.keys[key] = M.i32(el + 20 * k + 8)

    def row(self, key):
        r = self.keys.get(key)
        return None if r is None else self.rows + r * self.row_size

    def field(self, name):
        for f in self.fields:
            if f['Name'] == name:
                return f
        return None


def load_table(block, name):
    path = GX + block + '/pkgs/DataObject__Resident__' + name + '.uasset' if '/' not in block else block
    data = open(path, 'rb').read()
    z, e, m, d = cp.decode(data)
    content = bytearray(m.content)
    for (ni, num), offs in m.minimal_names:
        for o in offs:
            content[o:o + 8] = struct.pack('<II', name_id(z.names[ni]), num)
    base = alloc(len(content))
    M.write(base, bytes(content))
    holder = alloc(16)
    M.put64(holder + 8, base)
    return holder, d


# ---- TableCopies ----
class Copy:
    def __init__(self, holder):
        self.holder = holder
        self.original = M.i64(holder + 8)
        self.t = Table(self.original)
        n = self.t.count * self.t.row_size
        self.root = alloc(96 + n)
        self.rows = self.root + 96
        M.write(self.root, M.read(self.original, 88))
        for at in (0, 16, 40, 56, 72):
            v = M.i64(self.root + at)
            M.put64(self.root + at, encode(self.root + at, self.rows) if at == 72 else moved(self.original + at, self.root + at, v))
        M.write(self.rows, M.read(self.t.rows, n))
        for r in range(self.t.count):
            frm = self.t.rows + r * self.t.row_size
            to = self.rows + r * self.t.row_size
            for f in self.t.fields:
                if f['Array'] or f['Type'] == 10:
                    M.put64(to + f['Offset'], moved(frm + f['Offset'], to + f['Offset'], M.i64(to + f['Offset'])))
        self.edits = 0
        self.keep = []

    def row_of(self, key):
        g = self.t.row(key)
        return None if g is None else self.rows + (g - self.t.rows)

    def names_at(self, row, f):
        if f['Type'] != 11:
            return []
        if not f['Array']:
            return [M.read(row + f['Offset'], 8)]
        v, n = M.i64(row + f['Offset']), M.i32(row + f['Offset'] + 8)
        if n <= 0:
            return []
        data = resolve(row + f['Offset'], v)
        return [M.read(data + 8 * k, 8) for k in range(n)]

    def set_names(self, row, f, names):
        at = row + f['Offset']
        if not f['Array']:
            M.write(at, names[0] if names else bytes(8))
        else:
            lst = alloc(max(8, 8 * len(names)), 8)
            for k, nm in enumerate(names):
                M.write(lst + 8 * k, nm)
            M.put64(at, encode(at, lst) if names else 0)
            M.put32(at + 8, len(names)); M.put32(at + 12, len(names))
        self.edits += 1

    def set_text(self, row, f, text):
        at = row + f['Offset']
        b = (text + '\0').encode('utf-16-le')
        buf = alloc(len(b), 2)
        M.write(buf, b)
        M.put64(at, encode(at, buf)); M.put32(at + 8, len(b) // 2); M.put32(at + 12, len(b) // 2)
        self.edits += 1

    def set_number(self, row, f, value):
        fmt = {1: '<B', 2: '<B', 3: '<b', 4: '<H', 5: '<h', 6: '<I', 7: '<i', 8: '<q', 9: '<f'}[f['Type']]
        M.write(row + f['Offset'], struct.pack(fmt, value if f['Type'] == 9 else int(value)))
        self.edits += 1

    def copy_row(self, to, frm, keep):
        own = M.read(to, self.t.row_size)
        M.write(to, M.read(frm, self.t.row_size))
        for f in self.t.fields:
            if f['Array'] or f['Type'] == 10:
                M.put64(to + f['Offset'], moved(frm + f['Offset'], to + f['Offset'], M.i64(to + f['Offset'])))
        for f in keep:
            M.write(to + f['Offset'], own[f['Offset']:f['Offset'] + f['Size']])
        self.edits += 1

    def place(self):
        M.put64(self.holder + 8, self.root)


# ---- reading a table back from its holder (the game's view) ----
def read_value(at, f):
    def one(a, code):
        if code == 11:
            return text_of(M.read(a, 8))
        if code == 10:
            v, n = M.i64(a), M.i32(a + 8)
            if n == 0:
                return None
            return M.read(resolve(a, v), 2 * n).decode('utf-16-le')
        return M.read(a, SIZE[code][0])
    if f['Array']:
        v, n = M.i64(at), M.i32(at + 8)
        if n == 0:
            return []
        data = resolve(at, v)
        es = SIZE[f['Type']][0]
        return [one(data + k * es, f['Type']) for k in range(n)]
    return one(at, f['Type'])


def view(holder):
    t = Table(M.i64(holder + 8))
    return {k: {f['Name']: read_value(t.rows + r * t.row_size + f['Offset'], f) for f in t.fields} for k, r in t.keys.items()}


def main(compat, build):
    cfg = json.load(open(compat))
    c = cfg['characters'][0]
    specs = c['charaspecs']
    sources = {   # table -> where the installed game has it (the FPYS build for the tables it changes)
        'PlayerTable': 'tab3', 'PlannerEventChara': 'tab3', 'BikeCharaSpec': 'tab3', 'Equipment': 'fpys',
        'BattlePlayerParameter': build + '/tables/BattlePlayerParameter.uasset', 'BattleAbility': build + '/tables/BattleAbility.uasset',
        'PlannerEvent': 'fpys', 'PlannerEventVoiceList': 'fpys'}
    holders, before = {}, {}
    for name, block in sources.items():
        holders[name], _ = load_table(block, name)
        before[name] = view(holders[name])
    copies = {name: Copy(h) for name, h in holders.items()}
    # Characters::Edit
    names = 0
    defaults = [('PlayerTable', ['PlayerCharaSpec_Array', 'EventCharaSpec_Array', 'ChangeWeaponCharaSpec_Array']), ('PlannerEventChara', ['CharaSpecName']),
                ('BikeCharaSpec', ['RiderCharaSpecID_Array']), ('Equipment', ['CharaSpecID_Array'])]
    mapping = {raw(a): raw(b) for a, b in specs.items()}
    for table, fields in defaults:
        cpy = copies[table]
        for fname in fields:
            f = cpy.t.field(fname)
            assert f and f['Type'] == 11, (table, fname)
            for r in range(cpy.t.count):
                row = cpy.rows + r * cpy.t.row_size
                lst = cpy.names_at(row, f)
                new = [mapping.get(n, n) for n in lst]
                if new != lst:
                    names += sum(1 for a, b in zip(lst, new) if a != b)
                    cpy.set_names(row, f, new)
    for r in c['rows']:
        cpy = copies[r['table']]
        to, frm = cpy.row_of(r['row']), cpy.row_of(r['from'])
        assert to and frm, r
        cpy.copy_row(to, frm, [cpy.t.field(k) for k in r.get('keep', [])])
    for v in c['values']:
        cpy = copies[v['table']]
        f = cpy.t.field(v['field'])
        for rn in v['rows']:
            row = cpy.row_of(rn)
            assert row, rn
            val = v['value']
            if isinstance(val, list):
                cpy.set_names(row, f, [raw(x) for x in val])
            elif isinstance(val, str):
                if f['Type'] == 11:
                    cpy.set_names(row, f, [raw(val)])
                else:
                    cpy.set_text(row, f, val)
            else:
                cpy.set_number(row, f, val)
    for cpy in copies.values():
        if cpy.edits:
            cpy.place()
    after = {name: view(h) for name, h in holders.items()}
    # ---- the checks
    problems = 0
    def expect(cond, what):
        nonlocal problems
        if not cond:
            problems += 1
            if problems < 30:
                print('PROBLEM', what)
    mapped = lambda x: specs.get(x, x) if isinstance(x, str) else x
    named = {(t, f) for t, fs in defaults for f in fs}
    rowcopies = {(r['table'], r['row']): r for r in c['rows']}
    values = {}
    for v in c['values']:
        for rn in v['rows']:
            values[(v['table'], rn, v['field'])] = v['value']
    van_pp = view(load_table('van3', 'BattlePlayerParameter')[0])
    van_ab = view(load_table('van3', 'BattleAbility')[0])
    for table in sources:
        b, a = before[table], after[table]
        expect(set(a) == set(b), (table, 'keys'))
        for key in b:
            for field, old in b[key].items():
                want = old
                if (table, field) in named:
                    want = [mapped(x) for x in old] if isinstance(old, list) else mapped(old)
                if (table, key) in rowcopies:
                    rc = rowcopies[(table, key)]
                    want = b[rc['from']][field] if field not in rc.get('keep', []) else old
                if (table, key, field) in values:
                    want = values[(table, key, field)]
                    f = Table(M.i64(holders[table] + 8)).field(field)
                    if f['Type'] == 10 and isinstance(want, str):
                        want += '\0'   # (the game's texts count their terminating zero)
                expect(a[key][field] == want, (table, key, field, a[key][field], want))
    # the meaning: pt_Cloud is the game's own; the abilities are the game's own (their UniqueId kept)
    for field, v in van_pp['pt_Cloud'].items():
        expect(after['BattlePlayerParameter']['pt_Cloud'][field] == v, ('pt_Cloud not the game\'s', field))
    for r in c['rows']:
        if r['table'] != 'BattleAbility':
            continue
        for field, v in van_ab[r['row']].items():
            expect(after['BattleAbility'][r['row']][field] == v, ('ability not the game\'s', r['row'], field, after['BattleAbility'][r['row']][field], v))
    # the game's image untouched
    for table, h in holders.items():
        copy = copies[table]
        expect(view_root(copy.original) == before[table], (table, 'the game\'s image changed'))
    print('names mapped: %d; rows copied: %d; values: %d; tables placed: %s' % (
        names, len(c['rows']), len(values), ', '.join('%s (%d)' % (n, cpy.edits) for n, cpy in copies.items() if cpy.edits)))
    print('pt_Cloud PlayerCharaSpec_Array:', after['PlayerTable']['pt_Cloud']['PlayerCharaSpec_Array'])
    print('pt_Cloud EventCharaSpec_Array:', after['PlayerTable']['pt_Cloud']['EventCharaSpec_Array'])
    print('W_TSW_9001:', after['Equipment']['W_TSW_9001']['CharaSpecID_Array'])
    print('VO_PC0000_00_Cloud:', after['PlannerEventVoiceList']['VO_PC0000_00_Cloud'])
    print('BT_BVCLD_STARTBTL_0000 VoicePack:', after['PlannerEvent']['BT_BVCLD_STARTBTL_0000']['VoicePack'])
    print('PROBLEMS: %d' % problems)
    return problems


def view_root(root):
    holder = alloc(16)
    M.put64(holder + 8, root)
    return view(holder)


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1], sys.argv[2]) else 0)
