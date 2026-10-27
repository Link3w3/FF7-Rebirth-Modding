// A test pixel shader for the game's particle base pass (RM_Particle permutations, Niagara sprite/mesh vertex factories):
// same inputs and bindings as the game's TBasePassPS for RMI_Particle_Emit, a pulsing magenta glow out.
cbuffer View : register(b0)
{
    float View_PreExposure : packoffset(c164.y);
    float View_GameTime : packoffset(c172.z);
};
cbuffer Material : register(b4)
{
    float4 Material_VectorExpressions[42] : packoffset(c0);
    float4 Material_ScalarExpressions[8] : packoffset(c42);
};
SamplerState Material_Texture2D_1Sampler : register(s1);
Texture2D Material_Texture2D_1 : register(t2);

struct FParticleIn
{
    nointerpolation uint3 ParticleContext : PARTICLE_CONTEXT0;
    nointerpolation float2 Coverage : COVERAGE_CONTEXT0;
    float4 TangentX : TEXCOORD10;
    float4 TangentZ : TEXCOORD11;
    nointerpolation float3 ParticlePosition : PARTICLE_POSITION0;
    float4 UV : PARTICLE_NATIVE_COORDINATE0;
    float4 FlipBookUV : PARTICLE_FLIP_BOOK_COORDINATE0;
    nointerpolation float4 FlipBookFrame : PARTICLE_FLIP_BOOK_FRAME0;
    nointerpolation float4 Param1 : PARTICLE_INDEPENDENT_PARAMETER_1;
    nointerpolation float4 Param2 : PARTICLE_INDEPENDENT_PARAMETER_2;
    nointerpolation float4 Param4 : PARTICLE_INDEPENDENT_PARAMETER_4;
    nointerpolation float4 Param5 : PARTICLE_INDEPENDENT_PARAMETER_5;
};

float4 MainPS(FParticleIn In, float4 SvPosition : SV_Position, bool bFront : SV_IsFrontFace) : SV_Target0
{
    float4 tex = Material_Texture2D_1.Sample(Material_Texture2D_1Sampler, In.UV.xy);
    float pulse = 0.75 + 0.25 * sin(View_GameTime * 6.0);
    float3 c = float3(1.0, 0.1, 0.9) * tex.r * pulse * 4.0;
    return float4(c * View_PreExposure, 0.0);
}
