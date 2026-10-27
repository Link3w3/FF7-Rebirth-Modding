# the two FaceKH animations next to Event00 in Flatten Root's order: their tracks (did the pass move any under the root?)
AL = unreal.AnimationLibrary
sk = unreal.load_asset(SKEL)
out = {}
for n in ('F_0000EM', 'F_0001EM', 'F_0002M'):
    p = '/Game/Motion/Player/PC0000_00_Sora_KH2/FaceKH/%s.%s' % (n, n)
    a = unreal.load_asset(p)
    names = [str(x) for x in AL.get_animation_track_names(a)]
    out[n] = dict(tracks=len(names), first=names[:8], done=unreal.EditorAssetLibrary.get_metadata_tag(a, 'CaC.FlattenRoot.Done'))
# the root's children in the skeleton
ref = sk.get_editor_property('bone_tree') if False else None
import re
log = os.path.join(SAVED, 'Logs', 'End.log')
lines = open(log, encoding='utf-8', errors='replace').read().splitlines()
out['log'] = [l[:220] for l in lines if 'F_0000EM' in l or 'no track under the root' in l][-12:]
result = json.dumps(out, indent=1)
