import json, numpy as np, sys
sys.path[:0]=['/work/evil1013/tools','/work/cs']
import zenskel
d=json.load(open(sys.argv[1]))
print('pawn',d.get('pawn'),'restored',d['restored'])
print('ys mesh',d['ys']['mesh'],'| pc10 mesh',d['pc10']['mesh'])
sk=zenskel.bones(open('/work/seph1012/Game__Character__Player__PC0010_00_Sephiroth_Standard__Model__PC0010_00_Skeleton.uasset','rb').read())
S={b[0]:b for b in sk}
def ang(a,b):
    a=np.array(a);b=np.array(b); dd=abs(float(np.dot(a/np.linalg.norm(a),b/np.linalg.norm(b)))); return np.degrees(2*np.arccos(min(1.0,dd)))
Y={r['name']:r for r in d['ys']['rows']}; P={r['name']:r for r in d['pc10']['rows']}
print('%-28s %8s %8s %8s | %7s %7s %7s'%('bone','ys~ref','pc10~ref','ys~pc10','ys_len','pc_len','ref_len'))
for n in [r['name'] for r in d['pc10']['rows']]:
    if n not in Y or n not in S: continue
    ref=S[n][3]; y=Y[n]['l']; p=P[n]['l']
    if not isinstance(y,list) or not isinstance(p,list): continue
    a1=ang(y[3:7],ref); a2=ang(p[3:7],ref); a3=ang(y[3:7],p[3:7])
    yl=np.linalg.norm(y[0:3]); pl=np.linalg.norm(p[0:3]); rl=np.linalg.norm(S[n][2])
    flag=' <<' if abs(a1-a2)>5 or (rl>1 and abs(yl/0.8-pl)>1) else ''
    print('%-28s %8.1f %8.1f %8.1f | %7.2f %7.2f %7.2f%s'%(n,a1,a2,a3,yl,pl,rl,flag))
