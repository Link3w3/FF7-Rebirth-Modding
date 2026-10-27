import sys
sys.path[:0]=['/work/iostore','/work/cs','/work/swap1012/tools','/work/sephforms/tools','/work/weap1012/tools']
from iostore import Toc
from zen import Zen
import gameids
t=Toc(sys.argv[1])
want=sys.argv[2:]
for i in range(t.entries):
    p=t.files.get(i)
    if not p or not any(p.endswith(w) for w in want): continue
    d=t.read(i); z=Zen(d)
    pkg=p.replace('../../../End/Content/','/Game/').rsplit('.',1)[0]
    print('==',p, 'chunk %x'%t.chunk_id64(i), 'pkgid %x'%gameids.pkgid(pkg), 'flags %x'%z.flags, 'names',len(z.names),'exports',len(z.exports),'imports',len(z.imports), 'pkgname', z.mapped(z.name_mapped))
    print('  names:', z.names)
    for e in z.exports:
        print('   export',e['name'],'outer %x'%e['outer'],'gi %x'%e['global_import'], 'objhash %x'%gameids.objhash(pkg+'.'+e['name']))
