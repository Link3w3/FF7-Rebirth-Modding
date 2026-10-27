"""Rebuilds the game's VO_PC0010_00_Sephiroth banks (US and JP) from their own HCA streams with SoundBankCore and
compares the sab and the package with the game's, byte for byte."""
import sys, struct, os, subprocess
sys.path[:0]=['/work/vinsnd1016/tools','/work/vinvoice1016/tools','/work/cs']
import sead, sead2
from zen import Zen
W='/tmp/scratch/regen'
def run(lang, source):
    path='/work/youngvoice/game/Sound__Voice__%s__Character__Player__VO_PC0010_00_Sephiroth.uasset'%lang
    d=open(path,'rb').read()
    _,sab=sead.sab_of(d); sab=sab[:struct.unpack_from('<I',sab,0x0C)[0]]
    b=sead2.Bank(sab)
    lines=['bank %s %d'%(b.name,b.bank_id), 'package /Game/Sound/Voice/%s/Character/Player/VO_PC0010_00_Sephiroth'%lang,
           'alias /Game/Sound/Config/AliasSetting/VO_PC0010_00_Sephiroth', 'attenuation /Game/Sound/Config/Attenuation/player']
    if source: lines.append('source '+source)
    for i in range(len(b.snd)):
        sd=b.sound(i)
        m=b.material(b.material_of_sound(i))
        hca=m['extra'][16:]+m['stream']
        f='%s/%s_%d.hca'%(W,lang,i); open(f,'wb').write(hca)
        e=b.snd[i]
        lines.append('sound %s %r %d %d %s %d %r'%(sd['name'], sd['volume'], sab[e+6], sab[e+0x23], f, b.material_of_sound(i), sd['length']))
    open(W+'/spec_%s.txt'%lang,'w').write('\n'.join(lines)+'\n')
    r=subprocess.run(['./bank_regen',W+'/spec_%s.txt'%lang,W+'/%s.sab'%lang,W+'/%s.uasset'%lang],capture_output=True,text=True)
    print(lang, r.stdout.strip(), r.stderr.strip())
    mine=open(W+'/%s.sab'%lang,'rb').read()
    print('  sab', len(mine), len(sab), 'equal' if mine==sab else 'DIFFER')
    if mine!=sab:
        diffs=[i for i in range(min(len(mine),len(sab))) if mine[i]!=sab[i]]
        print('  first diffs', diffs[:20], len(diffs))
        for k in diffs[:6]: print('   @%x mine %02x game %02x'%(k,mine[k],sab[k]))
    pk=bytearray(open(W+'/%s.uasset'%lang,'rb').read())
    z0=Zen(d); zz=Zen(bytes(pk))
    pk[20:24]=d[20:24]; pk[zz.exp_off:zz.exp_off+8]=d[z0.exp_off:z0.exp_off+8]   # cooked header size (bookkeeping only)
    pk[-28:-12]=d[-28:-12]   # the compressed data guid (ours is our own)
    pk=bytes(pk)
    print('  package', len(pk), len(d), 'equal' if pk==d else 'DIFFER')
    if pk!=d:
        diffs=[i for i in range(min(len(pk),len(d))) if pk[i]!=d[i]]
        print('  diffs', len(diffs), 'ranges', diffs[:10], diffs[-10:])
        z=Zen(d); zm=Zen(pk)
        print('  header_end', zm.header_end, z.header_end, 'chs', zm.cooked_header_size, z.cooked_header_size)
        print('  names equal', zm.names==z.names, 'imports equal', zm.imports==z.imports)
        print('  export entry', zm.exports[0]==z.exports[0])
        for k in ('serial_offset','serial_size','name','cls','template','global_import','oflags'):
            if zm.exports[0][k]!=z.exports[0][k]: print('   ', k, zm.exports[0][k], z.exports[0][k])
        em, eg = zm.export_data(0), z.export_data(0)
        de=[i for i in range(min(len(em),len(eg))) if em[i]!=eg[i]]
        print('  export data', len(em), len(eg), 'diffs', len(de), de[:8], de[-8:])
run('US','/Game/Sound/Voice/JP/Character/Player/VO_PC0010_00_Sephiroth')
run('JP',None)
