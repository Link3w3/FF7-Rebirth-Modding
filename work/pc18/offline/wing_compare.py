"""Side-by-side renders of two kawaii runs' wings (distinct colours per wing part)."""
import sys
sys.path[:0]=['/work/pc18','/work/ccseph/tools','/work/pc18/offline']
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pc18_render as PR
from rerig import q2m
from analyze import load_run
from sim_render import skin
m=np.load('../pc18_rerig.npz')
runs=[(p.split(':')[0], load_run(p.split(':')[1])) for p in sys.argv[2].split(',')]
frames=[int(x) for x in sys.argv[3].split(',')]
yaws=[float(x) for x in (sys.argv[4] if len(sys.argv)>4 else '90').split(',')]
pos,tri,tmat,mats,names,joints=PR.load('../pc18_rerig.npz')
cols={'SU2050_02_BladeFlow':(0.9,0.2,0.2),'SU2050_02_WingDFlow':(0.95,0.6,0.1),'SU2050_02_WingBFlow':(0.2,0.7,0.2),'SU2050_02_WingAFlow':(0.6,0.4,0.9),'SU2050_02_WingCFlow':(0.1,0.6,0.9),'PC0010_00_Hair':(1,1,1),'SU2050_02_HeadPartsFlow':(0.3,0.3,0.8)}
cm={i:cols.get(n,(0.55,0.55,0.55)) for i,n in enumerate(mats)}
rows=[(lab,run,yaw) for lab,run in runs for yaw in yaws]
fig,axs=plt.subplots(len(rows),len(frames),figsize=(6*len(frames),7.5*len(rows)),squeeze=False)
for rr,(lab,run,yaw) in enumerate(rows):
    for c,f in enumerate(frames):
        R=np.array([q2m(q) for q in run[f,:,:4]]); P=run[f,:,4:].astype(float)
        pp=skin(m,R,P)
        PR.draw(axs[rr,c],pp,tri,tmat,cm,yaw,None,None,None,'%s frame %d yaw %d'%(lab,f,yaw))
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=int(sys.argv[5]) if len(sys.argv)>5 else 40); print('saved',sys.argv[1])
