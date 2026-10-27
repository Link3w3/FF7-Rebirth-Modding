"""Minimal UE4.26/4.27 IoStore reader (utoc/ucas) with Oodle via ooz."""
import struct, ctypes, sys, os
_lib = None
def oodle(data, us):
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL('/work/ooz/build/liblibooz.so')
        _lib.Ooz_Decompress.restype = ctypes.c_int
        _lib.Ooz_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    buf = ctypes.create_string_buffer(us + 64)
    r = _lib.Ooz_Decompress(data, len(data), buf, us, 0,0,0,None,0,None,None,None,0,0)
    assert r == us, (r, us)
    return buf.raw[:us]
def fstr(b,o):
    n=struct.unpack_from('<i',b,o)[0]; o+=4
    if n==0: return '',o
    if n>0: return b[o:o+n-1].decode('latin1'),o+n
    n=-n; return b[o:o+2*n-2].decode('utf-16le'),o+2*n
class Toc:
    def __init__(self, utoc, ucas=None):
        b=self.b=open(utoc,'rb').read()
        assert b[:16]==b'-==--==--==--==-'
        self.version=b[16]
        (self.hdrsize,self.entries,self.ncblocks,self.cblocksize,self.nmethods,self.methodlen,self.blocksz,self.diridxsize,self.partcount)=struct.unpack_from('<IIIIIIIII',b,20)
        self.container_id=struct.unpack_from('<Q',b,56)[0]
        self.flags=b[80]
        o=self.hdrsize
        self.chunk_ids=[b[o+12*i:o+12*i+12] for i in range(self.entries)]; o+=12*self.entries
        self.offlen=[]
        for i in range(self.entries):
            x=b[o+10*i:o+10*i+10]
            self.offlen.append((int.from_bytes(x[0:5],'big'),int.from_bytes(x[5:10],'big')))
        o+=10*self.entries
        self.blocks=[]
        for i in range(self.ncblocks):
            x=b[o+12*i:o+12*i+12]
            self.blocks.append((int.from_bytes(x[0:5],'little'),int.from_bytes(x[5:8],'little'),int.from_bytes(x[8:11],'little'),x[11]))
        o+=12*self.ncblocks
        self.methods=['None']+[b[o+self.methodlen*i:o+self.methodlen*(i+1)].rstrip(b'\0').decode() for i in range(self.nmethods)]; o+=self.methodlen*self.nmethods
        if self.flags & 0x4:
            hs=struct.unpack_from('<i',b,o)[0]; o+=4; o+=hs*2+20*self.ncblocks
        self.files={}
        if self.flags & 0x8 and self.diridxsize:
            d=b[o:o+self.diridxsize]; o+=self.diridxsize
            q=0; mount,q=fstr(d,q)
            n=struct.unpack_from('<i',d,q)[0]; q+=4
            dirs=[struct.unpack_from('<IIII',d,q+16*i) for i in range(n)]; q+=16*n
            n=struct.unpack_from('<i',d,q)[0]; q+=4
            fents=[struct.unpack_from('<III',d,q+12*i) for i in range(n)]; q+=12*n
            n=struct.unpack_from('<i',d,q)[0]; q+=4
            strs=[]
            for i in range(n):
                s,q=fstr(d,q); strs.append(s)
            def walk(di,path):
                name,child,sib,ff=dirs[di]
                nm=strs[name] if name!=0xffffffff else ''
                p=path+nm+'/' if nm else path
                f=ff
                while f!=0xffffffff:
                    fn,nxt,ud=fents[f]; self.files[ud]=mount+p+strs[fn]; f=nxt
                c=child
                while c!=0xffffffff:
                    walk(c,p); c=dirs[c][2]
            walk(0,'')
        self.metas_off=o
        self.ucas=ucas or utoc[:-5]+'.ucas'
    def chunk_type(self,i): return self.chunk_ids[i][11]
    def chunk_id64(self,i): return struct.unpack_from('<Q',self.chunk_ids[i],0)[0]
    def read(self,i):
        off,ln=self.offlen[i]
        first=off//self.blocksz; last=(off+ln-1)//self.blocksz if ln else first
        out=bytearray()
        with open(self.ucas,'rb') as f:
            for bi in range(first,last+1):
                boff,csz,usz,m=self.blocks[bi]
                f.seek(boff); raw=f.read((csz+15)&~15)[:csz]
                if m==0: out+=raw[:usz]
                else:
                    meth=self.methods[m]
                    assert meth.lower()=='oodle',meth
                    out+=oodle(raw,usz)
        start=off-first*self.blocksz
        return bytes(out[start:start+ln])
if __name__=='__main__':
    t=Toc(sys.argv[1])
    print('container %016x flags %d entries %d methods %s'%(t.container_id,t.flags,t.entries,t.methods))
    outdir=sys.argv[2] if len(sys.argv)>2 else None
    for i in range(t.entries):
        print(i,'%016x'%t.chunk_id64(i),'type',t.chunk_type(i),t.offlen[i],t.files.get(i,''))
        if outdir:
            os.makedirs(outdir,exist_ok=True)
            data=t.read(i)
            name=os.path.basename(t.files.get(i,'chunk%d_type%d.bin'%(i,t.chunk_type(i))))
            open(os.path.join(outdir,name),'wb').write(data)
