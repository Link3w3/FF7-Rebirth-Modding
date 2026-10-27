import sys,struct
sys.path.insert(0,'/work/crash1018')
from mdmp import Dump
dm=Dump(sys.argv[1])
print('regions',len(dm.memory), sum(s for _,s,_ in dm.memory))
for a in [0x7febfd529420,0x7febfd529498,0x7fedbdc157b0,0xc19376f5f0,0xc19376ee48,0x7fef1d930000-64]:
    b=dm.read(a,64)
    print(hex(a), b.hex() if b else None)
# stack of crashing thread
ex=dm.exception(); th=dm.threads[ex['tid']]
st=th['stack']; print('stack',hex(st[0]),hex(st[1]))
