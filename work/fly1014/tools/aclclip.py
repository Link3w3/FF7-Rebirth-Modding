"""Game (ACL-compressed) animations as KH2-tool Clips (clip.py): every bone with a track, local UE transforms per frame."""
import sys
sys.path[:0] = ['/work/acl', '/work/kh2/tools']
import numpy as np
import pose
from clip import Clip, SK_NAMES, SK_INDEX, REF_T, REF_Q, qmul, qnorm, qslerp, q_axis_angle, qrot, qconj

assert [b[0] for b in pose.BL] == SK_NAMES, 'the decoder and the clip tool use one skeleton'


def from_game(data, name=''):
    c, bones, LQ, LT = pose.load(data)
    names = [SK_NAMES[b] for b in bones]
    T = LT[:, bones].copy(); Q = LQ[:, bones].copy()
    S = np.ones_like(T)
    Q = np.where(Q[..., 3:4] < 0, -Q, Q)
    clip = Clip(names, T, Q, S, fps=float(round(c.sample_rate)), name=name)
    clip.source_rate = c.sample_rate
    return clip


def pose_distance(c, a, b, bones=None):
    """Mean angle (degrees) between frames a and b over the clip's bones (or the given ones)."""
    idx = [c.index[n] for n in bones] if bones else list(range(len(c.bones)))
    d = np.abs(np.sum(c.Q[a, idx] * c.Q[b, idx], -1)).clip(0, 1)
    return float(np.degrees(2 * np.arccos(d)).mean())
