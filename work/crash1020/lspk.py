import sys, struct
sys.path[:0]=['/work/iostore','/work/cs']
from iostore import Toc
from zen import Zen
import scriptobjs
so=scriptobjs.load()
so=so[0] if isinstance(so,tuple) else so
t=Toc(sys.argv[1])
for i in range(t.entries):
    if t.chunk_type(i)!=2: continue
    d=t.read(i)
    z=Zen(d)
    pkgname=z.names[z.name_mapped & 0xffffffff] if False else ''
    print('== chunk',i,t.files.get(i,''),'size',len(d),'exports',len(z.exports),'imports',len(z.imports))
    for e in z.exports:
        c=e['cls']; cn=so.get(c, '%016x'%c) if isinstance(so,dict) else c
        print('   %-40s %-60s ss=%d'%(e['name'], cn, e['serial_size']))
