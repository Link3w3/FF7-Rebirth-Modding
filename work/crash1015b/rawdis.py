import dis2, sys, re
d = dis2.d
def raw(rva, n=80):
    p = dis2.off(rva)
    code = d[p:p+n]
    for ins in dis2.md.disasm(code, rva):
        extra = ''
        m = re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
        if m:
            t = ins.address + ins.size + (int(m.group(2), 16) if m.group(1) == '+' else -int(m.group(2), 16))
            s = dis2.string_at(t)
            extra = '   ; %x %s' % (t, s or '')
        print('%8x: %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, extra))
        if ins.mnemonic in ('ret', 'int3'): break
if __name__ == '__main__':
    raw(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 80)
