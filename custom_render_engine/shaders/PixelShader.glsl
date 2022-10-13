// #version 430 /* inserted automatically by blender */

in vec4 vcolor; // vertex color
in vec3 normal;
in vec3 tangent;
in vec3 view;
in vec2 uv;
in float outline;

layout (location = 0) out vec4 color; // gl_FragColor

uniform mat4 directional_lights;
uniform float shading_sharpness;
uniform sampler2D tbasecolor;
uniform sampler2D tshadowtint;
uniform vec4 world_color;
uniform float fresnel_fac;

void main()
{
    if (outline > 0)
    {
        color = vec4(0, 0, 0, 1);
    } 
    else
    {
        vec3 base_color = texture(tbasecolor, uv).xyz;
        vec3 shadow_tint = texture(tshadowtint, uv).xyz;
        float fresnel = smoothstep(mix(0.33, 0.67, shading_sharpness), mix(1.0, 0.671, shading_sharpness), 1 - dot(normal, view)) * fresnel_fac;
        color.xyz = base_color * world_color.xyz * (1 + fresnel);
        for (int i = 0; i <= 3; ++i)
        {
            if (directional_lights[i].w > 0)
            {
                vec3 light = directional_lights[i].xyz;
                float nl = smoothstep(0, 1 - shading_sharpness, dot(normal, light));
                color.xyz += mix(base_color * shadow_tint, base_color, nl) * directional_lights[i].w * mix(1.0, 0.5, shading_sharpness);
            }
        }
        color.a = 1;
    }
}
