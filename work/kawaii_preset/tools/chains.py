"""The physics chains of a rig (Rebirth/Remake naming: bones ending in _Phy): each chain's root is a _Phy bone whose
parent is not one; its bones are the root's _Phy descendants (a tree)."""
import json, re, sys, collections


def load(path):
    r = json.load(open(path))
    bones = r['bones']
    by = {b['name']: b for b in bones}
    kids = collections.defaultdict(list)
    for b in bones:
        if b['parent']:
            kids[b['parent']].append(b['name'])
    return bones, by, kids


def is_phy(n):
    return n.endswith('_Phy')


def chains(bones, by, kids):
    out = []
    for b in bones:
        n = b['name']
        if is_phy(n) and not (b['parent'] and is_phy(b['parent'])):
            members = []
            stack = [n]
            while stack:
                x = stack.pop()
                members.append(x)
                stack.extend(k for k in kids[x] if is_phy(k))
            out.append((n, members))
    return out


PART = re.compile(r'^([LRC])_([A-Za-z]+?)([A-Z]{0,2})_([a-z]+)_Phy$')


def part_of(root):
    m = re.match(r'^([LRC])_([A-Za-z]+?)([A-Z]*\d*)_a_Phy$', root)
    if not m:
        m2 = re.match(r'^([LRC])_([A-Za-z]+)', root)
        return m2.group(2) if m2 else root
    return m.group(2)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        bones, by, kids = load(path)
        cs = chains(bones, by, kids)
        groups = collections.defaultdict(list)
        for root, mem in cs:
            groups[part_of(root)].append((root, len(mem), max(len(kids[m]) for m in mem)))
        print('== %s: %d bones, %d chains, %d _Phy bones' % (path.split('/')[-1], len(bones), len(cs), sum(len(m) for _, m in cs)))
        for g, items in sorted(groups.items()):
            print('   %-10s %2d: %s' % (g, len(items), ' '.join('%s(%d%s)' % (r.replace('_a_Phy', ''), n, '' if br <= 1 else ' branch') for r, n, br in items)))
