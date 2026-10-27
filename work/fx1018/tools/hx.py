"""hx.py <zen pkg> <export index> <start> [n]  - hex dump part of an export"""
import sys
sys.path[:0]=['/work/iostore','/work/cs','/work/fx1018/tools']
from zen import Zen
def hexdump(d,start,n,names=None):
    for o in range(start,min(start+n,len(d)),16):
        b=d[o:o+16]
        print('%6d  %-48s %s'%(o,b.hex(' '),''.join(chr(c) if 32<=c<127 else '.' for c in b)))
if __name__=='__main__':
    z=Zen(open(sys.argv[1],'rb').read())
    d=z.export_bytes(int(sys.argv[2]))
    hexdump(d,int(sys.argv[3]),int(sys.argv[4]) if len(sys.argv)>4 else 256)
