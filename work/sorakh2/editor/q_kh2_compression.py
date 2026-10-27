import unreal, json
ROOT = '/Game/Motion/Player/PC0000_00_Sora_KH2/Battle00'
names = ['0034', '1309', 'AirSpiral', 'FromCloud/B_AAttack01_0', 'FromCloud/B_Idle01_0']
out = {}
for n in names:
    p = ROOT + '/' + n
    a = unreal.EditorAssetLibrary.load_asset(p)
    if a is None:
        out[n] = 'missing'; continue
    r = {}
    for prop in ('bone_compression_settings', 'curve_compression_settings', 'additive_anim_type', 'interpolation',
                 'compression_scheme', 'enable_root_motion', 'force_root_lock', 'retarget_source', 'rate_scale',
                 'sequence_length', 'skeleton', 'do_not_override_compression', 'allow_frame_stripping'):
        try:
            v = a.get_editor_property(prop)
            r[prop] = v.get_path_name() if hasattr(v, 'get_path_name') else str(v)
        except Exception as e:
            r[prop] = 'ERR ' + str(e)[:80]
    try:
        r['num_frames'] = unreal.AnimationLibrary.get_num_frames(a)
    except Exception as e:
        r['num_frames'] = 'ERR ' + str(e)[:80]
    try:
        r['tracks'] = len(unreal.AnimationLibrary.get_animation_track_names(a))
    except Exception as e:
        r['tracks'] = 'ERR ' + str(e)[:80]
    out[n] = r
result = json.dumps(out, indent=1)
