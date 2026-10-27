"""Bahamut Fused Sephiroth's KawaiiPhysics with other mantle settings, for offline runs: make_bfs_kawaii.py's entry with
MANTLE and SHOULDER updated from a JSON of changes.
    tune_mantle.py <rerig.npz> <model object path> <out dir> '<{"mantle": {...}, "shoulder": {...}}>'"""
import json
import sys
sys.path.insert(0, '/work/bfs17')
import make_bfs_kawaii as K

src, model, out, changes = sys.argv[1:5]
c = json.loads(changes)
K.MANTLE.update(c.get('mantle', {}))
K.SHOULDER.update(c.get('shoulder', {}))
K.WINGS.update(c.get('wings', {}))
if 'tail_waves' in c:
    K.TAIL_WAVES = c['tail_waves']
if 'wing_beat' in c:
    K.WING_BEAT = c['wing_beat']
K.main(src, model, out)
