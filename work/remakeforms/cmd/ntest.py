# Test (nothing saved): can an editor script put the game's sound, voice and Niagara notifies with all their settings on
# an animation? A copy of a Remake animation in /Game/RebirthSkelCompat/_tmp, deleted at the end.
import json
EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
out = {}
src = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth/Battle00/B_Atk01'
dst = '/Game/RebirthSkelCompat/_tmp/NotifyTest'
try:
    if EAL.does_asset_exist(dst):
        EAL.delete_asset(dst)
    a = EAL.duplicate_asset(src, dst)
    out['dup'] = str(a)
    classes = {}
    for n in ('AnimNotifyState_EndTimedNiagaraEffect', 'EndAnimNotifyPlayCharacterSound', 'EndAnimNotifyPlayVoice', 'EndAnimNotifyPlayWeaponSound'):
        c = unreal.load_class(None, '/Script/EndGame.' + n)
        classes[n] = c
        out['class_' + n] = str(c)
    out['fx_asset_exists'] = EAL.does_asset_exist('/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Trail_01')
    out['se_bank_exists'] = EAL.does_asset_exist('/Game/Sound/SE/Character/Enemy/SE_EB0021_Sephroth')
    out['vo_bank_exists'] = EAL.does_asset_exist('/Game/Sound/Voice/JP/Character/Enemy/VO_EB0021_00_Sephiroth_Standard')
    AL.add_animation_notify_track(a, 'T1')
    se = AL.add_animation_notify_event(a, 'T1', 0.5, classes['EndAnimNotifyPlayCharacterSound'])
    out['se'] = str(se)
    tried = {}
    for nm in ('sound_name', 'SoundName'):
        try:
            se.set_editor_property(nm, 'EB0021_whoosh02'); tried[nm] = 'ok'
        except Exception as ex:
            tried[nm] = str(ex)[:150]
    for nm in ('attach_point_name',):
        try:
            se.set_editor_property(nm, 'L_Hand_a'); tried[nm] = 'ok'
        except Exception as ex:
            tried[nm] = str(ex)[:150]
    for label, val in (('path', unreal.SoftObjectPath('/Game/Sound/SE/Character/Enemy/SE_EB0021_Sephroth.SE_EB0021_Sephroth')),):
        try:
            se.set_editor_property('sound_ref', val); tried['sound_ref_' + label] = 'ok'
        except Exception as ex:
            tried['sound_ref_' + label] = str(ex)[:200]
    try:
        tried['sound_ref_now'] = str(se.get_editor_property('sound_ref'))
    except Exception as ex:
        tried['sound_ref_now'] = str(ex)[:200]
    out['se_set'] = tried
    fx = AL.add_animation_notify_state_event(a, 'T1', 0.6, 0.3, classes['AnimNotifyState_EndTimedNiagaraEffect'])
    out['fx'] = str(fx)
    t2 = {}
    try:
        p = fx.get_editor_property('m_niagara_create_params')
        t2['params_type'] = str(type(p))
        t2['params_fields'] = [x for x in dir(p) if not x.startswith('_')][:60]
        info = p.get_editor_property('m_niagara_parameter_info')
        t2['info_fields'] = [x for x in dir(info) if not x.startswith('_')][:40]
        t2['template_now'] = str(info.get_editor_property('m_template'))
        try:
            info.set_editor_property('m_template', unreal.SoftObjectPath('/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Trail_01.FX_PC0010_Weapon_Trail_01'))
            t2['template_set'] = 'ok'
        except Exception as ex:
            t2['template_set'] = str(ex)[:200]
        p.set_editor_property('m_niagara_parameter_info', info)
        p.set_editor_property('m_socket_name', 'C_TrailA_b')
        p.set_editor_property('m_location_offset', unreal.Vector(40, 0, 120))
        p.set_editor_property('m_rotation_offset', unreal.Rotator(70, 180, 0))
        fx.set_editor_property('m_niagara_create_params', p)
        t2['set'] = 'ok'
    except Exception as ex:
        t2['error'] = str(ex)[:300]
    try:
        fx.set_editor_property('m_attach_type', unreal.EndAnimNotifyAttachType.WEAPON1)
        t2['attach'] = 'ok'
    except Exception as ex:
        t2['attach'] = str(ex)[:200]
    out['fx_set'] = t2
    out['describe'] = json.loads(unreal.EndSkeletonCompatDataObject.describe_animations([dst + '.NotifyTest']))[0].get('notifies')
finally:
    try:
        EAL.delete_asset(dst)
        out['deleted'] = not EAL.does_asset_exist(dst)
    except Exception as ex:
        out['deleted'] = str(ex)[:200]
result = out
