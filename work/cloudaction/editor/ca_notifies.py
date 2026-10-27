# step 3: for jobs K, Cloud's settings that Import Key Animations does not set (bPoseAnimation, the behavior action blends,
# root motion and rate settings; the resource reference user data that keeps the effects of his notifies loaded) set on
# Sora's, then Copy Notifies Onto (Cloud's notifies, sync markers and curves as they are; it saves the animations).
PROPS = ('pose_animation', 'override_behavior_action_blend_time', 'override_behavior_action_blend_out_time',
         'override_behavior_action_blend_out_sequence_filter', 'root_motion_scale', 'rate_scale', 'enable_root_motion',
         'root_motion_root_lock', 'force_root_lock', 'use_normalized_root_motion_scale', 'interpolation')
out = []
for k in K:
    prs = pairs(k)
    notes = []
    for c, s in prs:
        ca, sa = unreal.load_asset(c), unreal.load_asset(s)
        if ca is None or sa is None:
            notes.append('%s: %s does not load' % (s, 'Cloud\'s' if ca is None else 'Sora\'s'))
            continue
        for prop in PROPS:
            try:
                v = ca.get_editor_property(prop)
            except Exception as e:
                continue
            if v != sa.get_editor_property(prop):
                sa.set_editor_property(prop, v)
                notes.append('%s: %s = %s' % (s.rsplit('.', 1)[1], prop, v))
        try:
            seq = ca.get_editor_property('override_behavior_action_blend_out_sequence')
            if seq is not None:
                mine = unreal.load_asset(obj(sora_of(seq.get_path_name())))
                sa.set_editor_property('override_behavior_action_blend_out_sequence', mine)
                notes.append('%s: blend out sequence %s -> %s' % (s.rsplit('.', 1)[1], seq.get_path_name(), mine.get_path_name() if mine else None))
        except Exception as e:
            notes.append('%s: blend out sequence: %s' % (s.rsplit('.', 1)[1], str(e)[:120]))
        try:
            uds = ca.get_editor_property('asset_user_data')
        except Exception as e:
            uds = []
            notes.append('%s: asset user data: %s' % (s.rsplit('.', 1)[1], str(e)[:120]))
        if uds:
            made = []
            for ud in uds:
                if ud is None:
                    continue
                try:
                    new = unreal.new_object(type(ud), sa)
                    for prop in ('assets',):
                        new.set_editor_property(prop, ud.get_editor_property(prop))
                    made.append(new)
                except Exception as e:
                    notes.append('%s: user data %s: %s' % (s.rsplit('.', 1)[1], ud.get_class().get_name(), str(e)[:160]))
            if made:
                sa.set_editor_property('asset_user_data', made)
                notes.append('%s: %d user data (%s)' % (s.rsplit('.', 1)[1], len(made), ', '.join('%d assets' % len(m.get_editor_property('assets')) for m in made)))
    rep = LIB.copy_notifies_onto([c for c, s in prs], [s for c, s in prs], True)
    out.append(dict(job=JOBS[k][0], n=len(prs), notes=notes, report=rep.strip().splitlines()[-1][:400] if rep.strip() else ''))
result = json.dumps(out, indent=1)
