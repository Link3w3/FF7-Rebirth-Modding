import unreal
out = {}
out['animlib_notify'] = sorted(n for n in dir(unreal.AnimationLibrary) if 'notify' in n.lower())
for cname in ('AnimNotifyState_EndTimedNiagaraEffect', 'EndAnimNotifyPlayCharacterSound', 'EndAnimNotifyPlayWeaponSound', 'EndAnimNotifyBattleDamage'):
    c = getattr(unreal, cname, None)
    out[cname] = 'missing' if c is None else str(c)
    if c is not None:
        try:
            cdo = unreal.get_default_object(c)
            props = [p for p in dir(cdo) if p.startswith('m_') or p in ('sound_name', 'attach_point_name', 'sound_ref', 'weapon_slot', 'b_follow', 'volume_multiplier')]
            out[cname + '_props'] = props[:60]
        except Exception as ex:
            out[cname + '_cdo'] = str(ex)
s = getattr(unreal, 'EndNiagaraCreateParams', None)
out['EndNiagaraCreateParams'] = str(s)
if s is not None:
    v = s()
    out['params_fields'] = [p for p in dir(v) if p.startswith('m_')]
    try:
        out['params_default'] = {k: str(v.get_editor_property(k)) for k in ('m_socket_name', 'm_location_offset', 'm_rotation_offset', 'm_scale', 'm_attached', 'm_notify_rotation_kind')}
    except Exception as ex:
        out['params_default_err'] = str(ex)
    try:
        info = v.get_editor_property('m_niagara_parameter_info')
        out['info_fields'] = [p for p in dir(info) if p.startswith('m_')]
        sp = unreal.SoftObjectPath('/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Trail_01.FX_PC0010_Weapon_Trail_01')
        out['softpath'] = str(sp)
        info.set_editor_property('m_template', sp)
        out['softpath_back'] = str(info.get_editor_property('m_template'))
        out['softpath_str'] = str(unreal.SystemLibrary.break_soft_object_path(info.get_editor_property('m_template')))
    except Exception as ex:
        out['info_err'] = str(ex)
e = getattr(unreal, 'EEndAnimNotifyAttachType', None) or getattr(unreal, 'EndAnimNotifyAttachType', None)
out['attach_enum'] = str(e) + ' ' + (str([m for m in dir(e) if m.isupper()]) if e else '')
result = out
