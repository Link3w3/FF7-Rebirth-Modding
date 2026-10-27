"""lea rcx,[reg+disp32] followed (within 16 bytes) by call rel32: the call targets.  leacalls.py <hex disp> [<hex disp>...]"""
import sys, struct, re, collections
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
data = p.data
for dh in sys.argv[1:]:
    disp = int(dh, 16)
    pat = re.compile(rb'\x48\x8D[\x88-\x8B\x8D-\x8F]' + re.escape(struct.pack('<I', disp)), re.S)
    targets = collections.defaultdict(list)
    for sec in [s for s in p.sections if s['code']]:
        start, end = sec['off'], sec['off'] + sec['rsize']
        for m in pat.finditer(data, start, end):
            o = m.end()
            va = sec['va'] + (m.start() - start)
            for ins in md.disasm(data[o:o + 24], sec['va'] + (o - start)):
                if ins.mnemonic == 'call':
                    targets[ins.op_str].append(va)
                    break
                if ins.mnemonic in ('ret', 'jmp') or 'rcx' in ins.op_str.split(',')[0]:
                    break
    print('disp %s:' % dh)
    for t, sites in sorted(targets.items(), key=lambda kv: -len(kv[1])):
        print('  %-20s %3d  %s' % (t, len(sites), ' '.join('%x' % s for s in sites[:6])))
