#define PI 3.1416

in vec2 uv;
uniform sampler2D tdepth;
uniform sampler2D tbasecolor;
uniform sampler2D tshadowcolor;
uniform sampler2D tworldnormal;
uniform sampler2D tmask;
uniform usampler2D tshadingmodel;

out vec4 color;

uniform mat4 mat_view_projection; 

#if DIRECTIONAL_LIGHT
uniform vec3 light_direction;
#endif

#if LOCAL_LIGHT
uniform vec3 light_location;
uniform float light_radius;
uniform float light_range;

uniform vec3 light_spot_direction;
uniform float light_spot_size;
uniform float light_spot_blend;
#endif

uniform float energy;
uniform vec3 light_color;

struct GBufferData
{
    vec3 BaseColor;
    vec3 ShadowColor;
    vec3 WorldNormal;
    vec3 WorldPos;
    uint ShadingModel;
};

struct LightData
{
    vec3 Color;
    float Falloff;
    float Intensity;
    vec3 FinalColor;
};

float MapRange(float x, float fromMin, float fromMax, float toMin, float toMax)
{
    return mix(toMin, toMax, (x - fromMin) / (fromMax - fromMin));
}

float ConeInterp(float x)
{
    return -1 * cos(x * PI / 2) + 1;
}

float saturate(float x) { return clamp(x, 0.f, 1.f); }

LightData GetLightData(GBufferData GBuffer, vec3 L)
{
    LightData Out;
    Out.Color = light_color;
    Out.Intensity = energy;
#if POINT_LIGHT || SPOT_LIGHT
    float Dist = length(light_location - GBuffer.WorldPos);
    Out.Falloff = 1 / (Dist * Dist);
    #if SPOT_LIGHT
        float ConeFalloff = clamp(MapRange(1 - dot(L, light_spot_direction), ConeInterp(light_spot_size), 0, 0, 1), 0, 1);
        Out.Falloff *= smoothstep(0, light_spot_blend, ConeFalloff);
    #endif
#else
    Out.Falloff = 1;
#endif
    Out.FinalColor = light_color * energy * Out.Falloff;
    return Out;
}

vec3 ScreenToWorldPos(vec2 ScreenCoords)
{
    vec4 pos;
    pos.w = 1;
    pos.xy = uv * 2 - 1;
    pos.z = texture(tdepth, ScreenCoords).r * 2 - 1;
    pos = inverse(mat_view_projection) * pos;
    pos /= pos.w;
    return pos.xyz;
}

GBufferData SampleScreenTextures(vec2 ScreenCoords)
{
    GBufferData OutBuffer;
    OutBuffer.BaseColor = texture(tbasecolor, ScreenCoords).rgb;
    OutBuffer.ShadowColor = texture(tshadowcolor, ScreenCoords).rgb;
    OutBuffer.WorldNormal = texture(tworldnormal, ScreenCoords).rgb;
    OutBuffer.WorldPos = ScreenToWorldPos(ScreenCoords);
    uint shadingmodel = texture(tshadingmodel, ScreenCoords).r;
    OutBuffer.ShadingModel = shadingmodel;
    return OutBuffer;
}

vec3 GetDirectLighting(GBufferData GBuffer, float NdotL, LightData Light)
{
    switch (GBuffer.ShadingModel)
    {
        default:
        case SHADINGMODEL_UNLIT:
            return vec3(0);
        case SHADINGMODEL_LAMBERT:
            return GBuffer.BaseColor * saturate(NdotL) * Light.FinalColor;
        case SHADINGMODEL_TOON:
            return mix(GBuffer.ShadowColor, GBuffer.BaseColor, ceil(NdotL)) * Light.FinalColor;
    }
}

void main()
{
    GBufferData GBuffer = SampleScreenTextures(uv);
    float NdotL = 0;
#if DIRECTIONAL_LIGHT
    vec3 L = light_direction;
#elif POINT_LIGHT || SPOT_LIGHT
    vec3 L = normalize(light_location - GBuffer.WorldPos);
#endif
    LightData Light = GetLightData(GBuffer, L);
    NdotL = dot(GBuffer.WorldNormal, L);
    color.rgb = GetDirectLighting(GBuffer, NdotL, Light);
    color.a = 1;
}