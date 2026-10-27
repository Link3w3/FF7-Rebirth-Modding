import struct, sys, legsum
def cooked_imports(d):
    p=0
    tag, legacy = struct.unpack_from('<Ii', d, p); p += 8
    if legacy != -4: p += 4
    ue4, lic = struct.unpack_from('<ii', d, p); p += 8
    n = struct.unpack_from('<i', d, p)[0]; p += 4 + n*20
    total = struct.unpack_from('<i', d, p)[0]; p += 4
    folder, p = legsum.fstring(d, p)
    flags = struct.unpack_from('<I', d, p)[0]; p += 4
    nc, no = struct.unpack_from('<ii', d, p); p += 8
    if not (flags & 0x80000000):
        loc, p = legsum.fstring(d, p)
    p += 8
    ec, eo, ic, io_, do = struct.unpack_from('<iiiii', d, p)
    names=[]; q=no
    for k in range(nc):
        s,q=legsum.fstring(d,q); q+=4; names.append(s)
    imps=[]
    for k in range(ic):
        cp,cpn,cn,cnn,outer,on,onn=struct.unpack_from('<iiiiiii', d, io_+28*k)
        imps.append((names[cn], outer, names[on]))
    def full(i):
        c,o,n=imps[i]
        return (full(-o-1)+'.' if o<0 else '')+n
    return [(c, full(i)) for i,(c,o,n) in enumerate(imps) if c!='Package']
if __name__=='__main__':
    for f in sys.argv[1:]:
        print('==', f.rsplit('/',1)[1])
        for c, n in cooked_imports(open(f,'rb').read()):
            if not n.startswith('/Game/Renderer/Texture'): print('   ', c, n)
