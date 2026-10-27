namespace S3520 {
using namespace cpuglsl;
static UBO& View = ubo("View");
static UBO& Primitive = ubo("Primitive");
static Tex3D View_SpatiotemporalBlueNoiseVolumeTexture{texid("View_SpatiotemporalBlueNoiseVolumeTexture")};
static Tex2D Material_Texture2D_0{texid("Material_Texture2D_0")};
static Tex2D Material_Texture2D_1{texid("Material_Texture2D_1")};
static Tex2D Material_Texture2D_2{texid("Material_Texture2D_2")};
static Tex2D Material_Texture2D_3{texid("Material_Texture2D_3")};
static Tex2D Material_Texture2D_4{texid("Material_Texture2D_4")};
static Samp View_SharedAnisotropic4XWrappedSampler{texid("View_SharedAnisotropic4XWrappedSampler")};
static vec4 TEXCOORD_10;
static vec4 TEXCOORD_11;
static vec4 TEXCOORD;
static D CONSTANT_CONTEXT;
static vec4 CURRENT_CLIP_SPACE_POSITION;
static vec4 PREVIOUS_CLIP_SPACE_POSITION;
static vec4 SV_Target;
static vec4 SV_Target_1;
static vec4 SV_Target_2;
static vec4 SV_Target_3;
static vec4 SV_Target_4;
static vec4 SV_Target_5;
static vec4 SV_Target_6;






void run()
{
    vec4 _117 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    vec4 _127 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _135 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _140 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _147 = (_140.x * 2.0) + (-1.0);
    D _149 = (_140.y * 2.0) + (-1.0);
    D _157 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_147, _149), vec2(_147, _149))));
    D _162 = inversesqrt(dot(vec3(_147, _149, _157), vec3(_147, _149, _157)));
    D _163 = _162 * _147;
    D _164 = _162 * _149;
    D _165 = _162 * _157;
    vec4 _168 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _173 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _179 = inversesqrt(dot(vec3(_163, _164, _165), vec3(_163, _164, _165)));
    D _180 = _179 * _163;
    D _181 = _179 * _164;
    D _182 = _179 * _165;
    D _185 = fma(_182, TEXCOORD_11.x, fma(_181, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _180 * TEXCOORD_10.x));
    D _188 = fma(_182, TEXCOORD_11.y, fma(_181, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _180 * TEXCOORD_10.y));
    D _191 = fma(_182, TEXCOORD_11.z, fma(_181, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _180 * TEXCOORD_10.z));
    D _195 = inversesqrt(dot(vec3(_185, _188, _191), vec3(_185, _188, _191)));
    D _196 = _195 * _185;
    D _197 = _195 * _188;
    D _198 = _195 * _191;
    D _203 = spvNClamp(_168.x, 0.0, 1.0);
    D _206 = dFdxFine(_196);
    D _207 = dFdxFine(_197);
    D _208 = dFdxFine(_198);
    D _212 = dFdyFine(_196);
    D _213 = dFdyFine(_197);
    D _214 = dFdyFine(_198);
    D _232 = (_117.x * 2.0) + (-1.0);
    D _243 = (1.0 - sqrt(1.0 - abs(_232))) * D(int(uint(_232 > 0.0) - uint(_232 < 0.0)));
    D _245 = (_117.y * 2.0) + (-1.0);
    D _256 = (1.0 - sqrt(1.0 - abs(_245))) * D(int(uint(_245 > 0.0) - uint(_245 < 0.0)));
    D _258 = (_117.z * 2.0) + (-1.0);
    D _269 = (1.0 - sqrt(1.0 - abs(_258))) * D(int(uint(_258 > 0.0) - uint(_258 < 0.0)));
    D _277 = spvNClamp((_196 * 0.5) + 0.5, 0.0, 1.0);
    D _278 = spvNClamp((_197 * 0.5) + 0.5, 0.0, 1.0);
    D _279 = spvNClamp((_198 * 0.5) + 0.5, 0.0, 1.0);
    D _326 = spvNClamp(((_185 * 0.5) * _195) + 0.5, 0.0, 1.0);
    D _327 = spvNClamp(((_188 * 0.5) * _195) + 0.5, 0.0, 1.0);
    D _328 = spvNClamp(((_191 * 0.5) * _195) + 0.5, 0.0, 1.0);
    D _398;
    D _399;
    if (CURRENT_CLIP_SPACE_POSITION.w != 0.0)
    {
        D _375 = 1.0 / CURRENT_CLIP_SPACE_POSITION.w;
        D _378 = 1.0 / PREVIOUS_CLIP_SPACE_POSITION.w;
        _398 = (spvNMin(spvNMax(((View._m0[154u].z - View._m0[154u].x) + (_375 * CURRENT_CLIP_SPACE_POSITION.x)) - (_378 * PREVIOUS_CLIP_SPACE_POSITION.x), -2.0), 2.0) * 0.249988555908203125) + 0.50000762939453125;
        _399 = (spvNMin(spvNMax(((View._m0[154u].w - View._m0[154u].y) + (_375 * CURRENT_CLIP_SPACE_POSITION.y)) - (_378 * PREVIOUS_CLIP_SPACE_POSITION.y), -2.0), 2.0) * 0.249988555908203125) + 0.50000762939453125;
    }
    else
    {
        _398 = 0.0;
        _399 = 0.0;
    }
    SV_Target.x = 0.0;
    SV_Target.y = 0.0;
    SV_Target.z = 0.0;
    SV_Target.w = 0.0;
    SV_Target_1.x = spvNClamp(((abs((_277 * 2.0) + (-1.0)) + (-0.9980449676513671875)) < 0.0) ? (_277 + (_243 * 0.000977517105638980865478515625)) : _277, 0.0, 1.0);
    SV_Target_1.y = spvNClamp(((abs((_278 * 2.0) + (-1.0)) + (-0.9980449676513671875)) < 0.0) ? (_278 + (_256 * 0.000977517105638980865478515625)) : _278, 0.0, 1.0);
    SV_Target_1.z = spvNClamp(((abs((_279 * 2.0) + (-1.0)) + (-0.9980449676513671875)) < 0.0) ? (_279 + (_269 * 0.000977517105638980865478515625)) : _279, 0.0, 1.0);
    SV_Target_1.w = 0.66666662693023681640625;
    SV_Target_2.x = spvNClamp(_135.x, 0.0, 1.0);
    SV_Target_2.y = 0.0;
    SV_Target_2.z = sqrt(spvNClamp(spvNMin((dot(vec3(_212, _213, _214), vec3(_212, _213, _214)) + dot(vec3(_206, _207, _208), vec3(_206, _207, _208))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_203 * _203), 0.0, 1.0));
    SV_Target_2.w = D(((floatBitsToUint(Primitive._m0[27u]).z << 4u) & 48u) | 1u) * 0.0039215688593685626983642578125;
    SV_Target_3.x = spvNClamp(_127.x, 0.0, 1.0);
    SV_Target_3.y = spvNClamp(_127.y, 0.0, 1.0);
    SV_Target_3.z = spvNClamp(_127.z, 0.0, 1.0);
    SV_Target_3.w = spvNClamp(_173.x, 0.0, 1.0);
    SV_Target_4.x = 0.0;
    SV_Target_4.y = 0.4000000059604644775390625;
    SV_Target_4.z = 0.0;
    SV_Target_4.w = 0.0;
    SV_Target_5.x = spvNClamp(((abs((_326 * 2.0) + (-1.0)) + (-0.99215686321258544921875)) < 0.0) ? (_326 + (_243 * 0.0039215688593685626983642578125)) : _326, 0.0, 1.0);
    SV_Target_5.y = spvNClamp(((abs((_327 * 2.0) + (-1.0)) + (-0.99215686321258544921875)) < 0.0) ? (_327 + (_256 * 0.0039215688593685626983642578125)) : _327, 0.0, 1.0);
    SV_Target_5.z = spvNClamp(((abs((_328 * 2.0) + (-1.0)) + (-0.99215686321258544921875)) < 0.0) ? (_328 + (_269 * 0.0039215688593685626983642578125)) : _328, 0.0, 1.0);
    SV_Target_5.w = 0.0;
    SV_Target_6.x = _398;
    SV_Target_6.y = _399;
    SV_Target_6.z = 0.0;
    SV_Target_6.w = 0.0;
}



void set_inputs(Inputs& in) {
    in.get("TEXCOORD_10", TEXCOORD_10);
    in.get("TEXCOORD_11", TEXCOORD_11);
    in.get("TEXCOORD", TEXCOORD);
    in.get("CONSTANT_CONTEXT", CONSTANT_CONTEXT);
    in.get("CURRENT_CLIP_SPACE_POSITION", CURRENT_CLIP_SPACE_POSITION);
    in.get("PREVIOUS_CLIP_SPACE_POSITION", PREVIOUS_CLIP_SPACE_POSITION);
}
void get_outputs(Outputs& o) {
    o.put("SV_Target", SV_Target);
    o.put("SV_Target_1", SV_Target_1);
    o.put("SV_Target_2", SV_Target_2);
    o.put("SV_Target_3", SV_Target_3);
    o.put("SV_Target_4", SV_Target_4);
    o.put("SV_Target_5", SV_Target_5);
    o.put("SV_Target_6", SV_Target_6);
}
} // namespace S3520