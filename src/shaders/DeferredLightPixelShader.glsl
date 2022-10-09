in vec2 uv;
uniform sampler2D tbasecolor;
uniform sampler2D tshadowcolor;
uniform sampler2D tworldnormal;
uniform sampler2D tmask;

out vec4 color;

#if DIRECTIONAL_LIGHT
uniform vec3 light_direction;
#endif

uniform float energy;

struct GBufferData
{
    vec3 BaseColor;
    vec3 ShadowColor;
    vec3 WorldNormal;
};

struct GBufferData SampleScreenTextures(vec2 ScreenCoords)
{
    struct GBufferData OutBuffer;
    OutBuffer.BaseColor = texture(tbasecolor, ScreenCoords).rgb;
    OutBuffer.ShadowColor = texture(tshadowcolor, ScreenCoords).rgb;
    OutBuffer.WorldNormal = texture(tworldnormal, ScreenCoords).rgb;
    return OutBuffer;
}

void main()
{
    struct GBufferData GBuffer = SampleScreenTextures(uv);
    color.rgb = GBuffer.BaseColor * vec3(dot(GBuffer.WorldNormal, light_direction)) * energy * texture(tmask, uv).x;
    color.a = 1;
}