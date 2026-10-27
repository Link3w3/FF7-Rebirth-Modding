"""Makes the Safer form's editor files next to the Bizarro ones (run on the PC, in Tools/SephirothForms):
safer/forms_import.json (his forms with SAFER), safer/only.json, build_safer_form.py, run_safer_form.ps1."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'safer'), exist_ok=True)

# ---- forms: the installed ones plus SAFER
forms = json.load(open(os.path.join(HERE, 'bizarro', 'forms_import.json')))
row = forms['animation_sets'][0]
lst = row['forms']['list']
assert [f['name'] for f in lst] == ['NORMAL', 'WINGED', 'FLYING', 'KH2', 'BIZARRO'], [f['name'] for f in lst]
FX = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/'
FX10 = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/'
FEATHERS = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_01.FX_EV_FOREE_7250_BlackFeather_01'
FEATHER_AURA = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_Aura_01.FX_EV_FOREE_7250_BlackFeather_Aura_01'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
VOICE = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth'
SCALE = 0.4
GROW = round(1.0 / SCALE, 3)   # effects made for Sephiroth's size, on Safer's scaled mesh
safer = {
    'name': 'SAFER', 'pack': 'Battle06',
    'model': '/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999.PC0010_999',
    'anim_class': '/Game/BluePrint/Animation/Player/PC0010_999_Safer_Sephiroth_Standard_Animation.PC0010_999_Safer_Sephiroth_Standard_Animation_C',
    'scale': SCALE,
    # (editor 1.12.1, Build Moves) his model, made facing +Y and floating high, turned to face the game's way and brought
    # down so his lowest feathers touch the ground
    'model_turn': -90.0, 'model_lift': -340.0,
    'hide_weapon': True,
    'effects': [{'effect': FX10 + 'FX_PC0010_10_Tenshi_Charge_01.FX_PC0010_10_Tenshi_Charge_01', 'scale': GROW},
                {'effect': FX + 'FX_PC0010_Limit01_BodyAura_01.FX_PC0010_Limit01_BodyAura_01', 'scale': GROW},
                {'effect': FEATHERS, 'socket': 'C_Hip_a', 'scale': GROW}, {'effect': FEATHER_AURA, 'scale': GROW}],
    'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_1_jump'}, {'bank': VOICE, 'cue': 'Atk_Ability_01'}],
    'super_armor': True, 'seconds': 60, 'cooldown': 30,
}
row['forms']['list'] = lst + [safer]
json.dump(forms, open(os.path.join(HERE, 'safer', 'forms_import.json'), 'w'), indent=1)
moves = json.load(open(os.path.join(HERE, 'safer', 'safer_moves.json')))
json.dump(sorted(m['name'] for m in moves['moves'] if m['build']), open(os.path.join(HERE, 'safer', 'only.json'), 'w'), indent=1)

# ---- build_safer_form.py: build_bizarro_form.py with Safer's moves (Battle06) built, and his model's folder labelled
s = open(os.path.join(HERE, 'build_bizarro_form.py'), encoding='utf-8').read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old, s.count(old))
    s = s.replace(old, new)
head_end = s.index('import json, os, struct, traceback')
s = ('''# Your playable Sephiroth's Safer form (animation pack Battle06): puts his forms (with SAFER) in the SephirothForms data
# object and builds Safer Sephiroth's moves (safer\\safer_moves.json, made by make_safer_moves.py) on his skeleton, his model
# turned to face the game's way and brought down (the SAFER form's Model Turn and Model Lift), and labels his model's folder
# (model, skeleton, wing physics, materials, textures) for chunk 49 so packaging puts them in pakchunk49.
# Run by run_safer_form.cmd (editor closed). Needs Create a Character System editor 1.12.1.
# Results: Saved\\RebirthSkelCompat\\SephirothForms\\safer_result.json, safer_build.txt, import_forms.txt, export_json.txt, validate.txt
# safer\\only.json (a list of move names), when there: only those are built.
''' + s[head_end:])
rep("BIZARRO = json.load(open(os.path.join(HERE, 'bizarro', 'bizarro_moves.json')))",
    "BIZARRO = json.load(open(os.path.join(HERE, 'bizarro', 'bizarro_moves.json')))\nSAFER = json.load(open(os.path.join(HERE, 'safer', 'safer_moves.json')))\nSAFER_FOLDER = '/Game/Character/Player/PC0010_999_Safer_Sephiroth'\nSAFER_CHUNK = 49")
rep("FORMS_FILE = os.path.join(HERE, 'bizarro', 'forms_import.json')", "FORMS_FILE = os.path.join(HERE, 'safer', 'forms_import.json')")
rep("ONLY_FILE = os.path.join(HERE, 'bizarro', 'only.json')", "ONLY_FILE = os.path.join(HERE, 'safer', 'only.json')")
rep("RESULT = os.path.join(OUT, 'bizarro_result.json')", "RESULT = os.path.join(OUT, 'safer_result.json')")
rep("unreal.log('BIZARRO %s: %s'", "unreal.log('SAFER %s: %s'")
rep("""        unreal.EndAnimSetMove().get_editor_property('clip_start')
    except Exception:
        raise RuntimeError('this editor has no clips on built moves: build the Create a Character System plugin 1.11 first')""",
    """        unreal.EndAnimSetMove().get_editor_property('clip_start')
        unreal.EndCharacterForm().get_editor_property('model_turn')
    except Exception:
        raise RuntimeError('this editor has no Model Turn on forms: build the Create a Character System plugin 1.12.1 first')""")
rep("""               '/Game/DataAsset/Game/CharaSpec']""", """               '/Game/DataAsset/Game/CharaSpec', '/Game/Motion/Player/PC0010_999_Safer_Sephiroth', SAFER_FOLDER]""")
rep("""    for item in BIZARRO['moves']:
        moves.append(make_move(item))
    setp(row, 'moves', moves)""", """    for item in BIZARRO['moves'] + SAFER['moves']:
        moves.append(make_move(item))
    setp(row, 'moves', moves)""")
rep("""    log('row', '%d moves, %d of them the Bizarro form\\'s (Battle05)' % (len(moves), len(BIZARRO['moves'])))""",
    """    log('row', '%d moves, %d of them the Bizarro form\\'s (Battle05), %d the Safer form\\'s (Battle06)' % (len(moves), len(BIZARRO['moves']), len(SAFER['moves'])))""")
rep("""    if 'BIZARRO' not in names:""", """    if 'BIZARRO' not in names or 'SAFER' not in names:""")
rep("""    todo = [m for m in BIZARRO['moves'] if m['build'] and (ONLY is None or m['name'] in ONLY)]""",
    """    todo = [m for m in SAFER['moves'] if m['build'] and (ONLY is None or m['name'] in ONLY)]""")
rep("""    open(os.path.join(OUT, 'bizarro_build.txt'), 'w', encoding='utf-8').write('\\n'.join(lines) + '\\n')""",
    """    open(os.path.join(OUT, 'safer_build.txt'), 'w', encoding='utf-8').write('\\n'.join(lines) + '\\n')""")
rep("""    checked, broken = broken_animations([PLAN['build_folder'] + '/Battle05'])""",
    """    checked, broken = broken_animations([PLAN['build_folder'] + '/Battle06'])""")
# the label for his model's folder, before the build (a problem with it stops the run in seconds, not after the moves)
rep("""    # 3. Build the Bizarro form's moves (the other forms' moves are in the project already).""", """    # 2b. His model's folder (model, skeleton, wing physics, materials, textures, and what they use that is not the game's,
    # wherever it is): chunk SAFER_CHUNK when the project is packaged (only what the game does not have goes in his pak)
    label_name = 'PAL_Safer_Chunk%d' % SAFER_CHUNK
    label_path = SAFER_FOLDER + '/' + label_name
    if unreal.EditorAssetLibrary.does_asset_exist(label_path):
        label = unreal.EditorAssetLibrary.load_asset(label_path)
    else:
        factory = unreal.DataAssetFactory()
        try:
            setp(factory, 'data_asset_class', unreal.PrimaryAssetLabel.static_class())
        except Exception:
            pass   # (the class given to create_asset makes it then)
        label = unreal.AssetToolsHelpers.get_asset_tools().create_asset(label_name, SAFER_FOLDER, unreal.PrimaryAssetLabel, factory)
    if label is None:
        raise RuntimeError('could not make ' + label_path)
    rules = getp(label, 'rules')
    setp(rules, 'chunk_id', SAFER_CHUNK)
    setp(rules, 'priority', max(1, getp(rules, 'priority')))
    setp(rules, 'cook_rule', unreal.PrimaryAssetCookRule.ALWAYS_COOK)
    setp(rules, ['apply_recursively', 'b_apply_recursively'], True)
    setp(label, 'rules', rules)
    setp(label, ['label_assets_in_my_directory', 'b_label_assets_in_my_directory'], True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(label, False):
        raise RuntimeError('could not save ' + label_path)
    log('label', '%s: chunk %d, cook always, the assets in its folder and what they use' % (label_path, getp(getp(label, 'rules'), 'chunk_id')))

    # 3. Build the Safer form's moves (the other forms' moves are in the project already).""")
open(os.path.join(HERE, 'build_safer_form.py'), 'w', encoding='utf-8').write(s)

# ---- run_safer_form.ps1
p = open(os.path.join(HERE, 'run_bizarro_form.ps1'), encoding='utf-8').read()
for a, b in (("build_bizarro_form.py", "build_safer_form.py"), ("bizarro_result.json", "safer_result.json"), ("bizarro_editor", "safer_editor"),
             ("bizarro_status.txt", "safer_status.txt"), ("run_bizarro_form.cmd", "run_safer_form.cmd")):
    assert a in p, a
    p = p.replace(a, b)
for a, b in (("AddMinutes(120)", "AddMinutes(300)"), ("TIMEOUT after 120 minutes", "TIMEOUT after 300 minutes"),   # 186 moves, not 39
             ("    Say ('   checked: ' + $Json.checked)", "    if ($Json.PSObject.Properties.Name -contains 'label') { Say ('   label: ' + $Json.label) }\n    Say ('   checked: ' + $Json.checked)")):
    assert p.count(a) == 1, a
    p = p.replace(a, b)
assert 'bizarro' not in p.lower(), [l for l in p.split('\n') if 'bizarro' in l.lower()]
open(os.path.join(HERE, 'run_safer_form.ps1'), 'w', encoding='utf-8', newline='\r\n').write(p.replace('\r\n', '\n'))
print('safer/forms_import.json: forms', [f['name'] for f in row['forms']['list']], '; safer/only.json:', len(json.load(open(os.path.join(HERE, 'safer', 'only.json')))), 'moves; build_safer_form.py, run_safer_form.ps1 written')
