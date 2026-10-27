DIR = '/Game/RebirthLighting'
TEX = DIR + '/Textures/'
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
CODE = "// FINAL FANTASY VII REBIRTH's SDR tonemapping (from its FTonemapPS): the exposed scene colour and glare, natural\n// vignetting, PQ encoding (1.0 = 100 nits), then the area colour LUT (BT.709 PQ -> ACES BT.2020 PQ 1000 nits, graded,\n// e.g. the menu's 030-SLUM7_day_HDR) and the output LUT (ACES BT.2020 PQ -> sRGB), both 32^3 and looked up like the\n// game (31/32 scale + half texel, trilinear). The LUTs are 1024 x 32 strips: blue picks the 32-texel tile.\nfloat Scale = View.OneOverPreExposure * Exposure;\nfloat3 C = (SceneColor.rgb + Bloom.rgb * BloomScale) * Scale;\nfloat2 Ndc = UV * 2.0 - 1.0;\nfloat2 Tn = Ndc * float2(1.0 / View.ViewToClip[0][0], 1.0 / View.ViewToClip[1][1]);\nfloat Cos2 = 1.0 / (dot(Tn, Tn) + 1.0);\nC *= 1.0 + (Cos2 * Cos2 - 1.0) * VignetteIntensity;\nfloat3 X = pow(saturate(C * 0.01), 0.1593017578125);\nfloat3 E = saturate(pow(max(0.0, (0.8359375 + 18.8515625 * X) / (1.0 + 18.6875 * X)), 78.84375));\nfloat3 P = E * 0.96875 + 0.015625;\nfloat B = P.z * 32.0 - 0.5;\nfloat B0 = clamp(floor(B), 0.0, 31.0);\nfloat B1 = min(B0 + 1.0, 31.0);\nfloat FB = saturate(B - B0);\nfloat3 G = lerp(LUTA.SampleLevel(LUTASampler, float2((P.x + B0) / 32.0, P.y), 0).rgb, LUTA.SampleLevel(LUTASampler, float2((P.x + B1) / 32.0, P.y), 0).rgb, FB);\nP = G * 0.96875 + 0.015625;\nB = P.z * 32.0 - 0.5;\nB0 = clamp(floor(B), 0.0, 31.0);\nB1 = min(B0 + 1.0, 31.0);\nFB = saturate(B - B0);\nreturn saturate(lerp(LUTB.SampleLevel(LUTBSampler, float2((P.x + B0) / 32.0, P.y), 0).rgb, LUTB.SampleLevel(LUTBSampler, float2((P.x + B1) / 32.0, P.y), 0).rgb, FB));\n"
out = {}

def make_material(name):
    path = DIR + '/' + name
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    return AT.create_asset(name, DIR, unreal.Material, unreal.MaterialFactoryNew())

# the tonemapper
m = make_material('M_RebirthTonemapper')
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_REPLACING_TONEMAPPER)
m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
def node(cls, x, y):
    return MEL.create_material_expression(m, cls, x, y)
sc = node(unreal.MaterialExpressionSceneTexture, -900, -200)
sc.set_editor_property('scene_texture_id', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
bl = node(unreal.MaterialExpressionSceneTexture, -900, 0)
bl.set_editor_property('scene_texture_id', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT2)
ea = node(unreal.MaterialExpressionEyeAdaptation, -900, 200)
sp = node(unreal.MaterialExpressionScreenPosition, -900, 300)
la = node(unreal.MaterialExpressionTextureObjectParameter, -900, 450)
la.set_editor_property('parameter_name', 'AreaLUT')
la.set_editor_property('texture', unreal.load_asset(TEX + 'T_RebirthLUT_SLUM7_day'))
la.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
lb = node(unreal.MaterialExpressionTextureObjectParameter, -900, 650)
lb.set_editor_property('parameter_name', 'OutputLUT')
lb.set_editor_property('texture', unreal.load_asset(TEX + 'T_RebirthLUT_ACES_sRGB'))
lb.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
vi = node(unreal.MaterialExpressionScalarParameter, -900, 850)
vi.set_editor_property('parameter_name', 'VignetteIntensity')
vi.set_editor_property('default_value', 0.33333298563957214)
bs = node(unreal.MaterialExpressionScalarParameter, -900, 950)
bs.set_editor_property('parameter_name', 'BloomScale')
bs.set_editor_property('default_value', 1.0)
cu = node(unreal.MaterialExpressionCustom, -400, 200)
cu.set_editor_property('code', CODE)
cu.set_editor_property('description', 'Rebirth Tonemap')
cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
ins = []
for n in ['SceneColor', 'Bloom', 'Exposure', 'UV', 'LUTA', 'LUTB', 'VignetteIntensity', 'BloomScale']:
    ci = unreal.CustomInput()
    ci.set_editor_property('input_name', n)
    ins.append(ci)
cu.set_editor_property('inputs', ins)
links = [(sc, 'Color', 'SceneColor'), (bl, 'Color', 'Bloom'), (ea, '', 'Exposure'), (sp, 'ViewportUV', 'UV'), (la, '', 'LUTA'), (lb, '', 'LUTB'), (vi, '', 'VignetteIntensity'), (bs, '', 'BloomScale')]
out['links'] = [MEL.connect_material_expressions(a, o, cu, i) for a, o, i in links]
out['emissive'] = MEL.connect_material_property(cu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
MEL.recompile_material(m)
EAL.save_loaded_asset(m)

# the sky backdrop: the environment cube, unlit, as the game's menu sky
k = make_material('M_RebirthSkyBackdrop')
k.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
k.set_editor_property('two_sided', True)
try:
    k.set_editor_property('is_sky', True)
except Exception as e:
    out['is_sky'] = str(e)
cv = MEL.create_material_expression(k, unreal.MaterialExpressionCameraVectorWS, -900, 0)
neg = MEL.create_material_expression(k, unreal.MaterialExpressionMultiply, -700, 0)
neg.set_editor_property('const_b', -1.0)
cube = MEL.create_material_expression(k, unreal.MaterialExpressionTextureSampleParameterCube, -500, 0)
cube.set_editor_property('parameter_name', 'Sky')
cube.set_editor_property('texture', unreal.load_asset(TEX + 'T_MenuSky_Day_Ambient0'))
cube.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
inten = MEL.create_material_expression(k, unreal.MaterialExpressionScalarParameter, -500, 250)
inten.set_editor_property('parameter_name', 'Intensity')
inten.set_editor_property('default_value', 1.0)
mul = MEL.create_material_expression(k, unreal.MaterialExpressionMultiply, -250, 0)
out['sky_links'] = [MEL.connect_material_expressions(cv, '', neg, 'A'), MEL.connect_material_expressions(neg, '', cube, 'UVs'),
                    MEL.connect_material_expressions(cube, 'RGB', mul, 'A'), MEL.connect_material_expressions(inten, '', mul, 'B'),
                    MEL.connect_material_property(mul, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)]
MEL.recompile_material(k)
EAL.save_loaded_asset(k)

w = unreal.EditorLevelLibrary.get_editor_world()
out['level'] = w.get_path_name()
out['level_dirty'] = w.get_outermost().is_dirty()
result = out
