"""ch049's clips in Unreal component space (cm, facing +X), cached: clipdata.load() -> {name: dict(fps, loop, W [f, n, 4, 4])},
bone names and parents (the imported skeleton's order)."""
import glob, json, os, pickle, sys
import numpy as np
sys.path.insert(0, '/work/ch049anim')
import unity_anim as U
import convert_ch049_anims as CV

UP = '/tmp/scratch'
CHAR = glob.glob(UP + '*character.049_001.d')[0]
MOTION = glob.glob(UP + '*character.049.motion.d')[0]
MODEL = '/work/unityrip/out/model/model.json'
CACHE = '/work/ys/clipdata.pkl'


def load():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    rig = U.load_rig(CHAR)
    bones = json.load(open(MODEL))['bones']
    names = [b['name'] for b in bones]
    parents = [b['parent'] for b in bones]
    rig_of = [rig.index[n] for n in names]
    is_root = [p < 0 for p in parents]
    clips = {}
    for a in U.clips(MOTION):
        d = U.decode(a, rig)
        Wu = U.world(d['T'], d['Q'], d['S'], rig.parents)[:, rig_of]
        W = CV.ue_world(Wu, rig_of, is_root)
        clips[a.m_Name[len('anim_ch049_'):]] = dict(fps=d['fps'], loop=d['loop'], W=W.astype(np.float32))
    data = dict(names=names, parents=parents, clips=clips)
    pickle.dump(data, open(CACHE, 'wb'))
    return data
