
in vec4 color;
in vec3 normal;
in vec3 view;
in vec2 uv;
in float outline;

uniform mat4 directional_lights;
uniform float shading_sharpness;
uniform bool use_tbasecolor;
uniform bool use_tshadowtint;
uniform sampler2D tbasecolor;
uniform sampler2D tshadowtint;
uniform vec4 world_color;

void main()
{
    if (outline > 0)
    {
        gl_FragColor = vec4(0, 0, 0, 1);
    } 
    else
    {
        vec3 base_color = use_tbasecolor ? texture(tbasecolor, uv).xyz : vec3(1, 1, 1);
        vec3 shadow_tint = use_tshadowtint ? texture(tshadowtint, uv).xyz : vec3(0, 0, 0);
        gl_FragColor.xyz = base_color * world_color.xyz;
        for (int i = 0; i <= 3; ++i)
        {
            if (directional_lights[i].w > 0)
            {
                vec3 light = directional_lights[i].xyz;
                float nl = smoothstep(0, 1 - shading_sharpness, dot(normal, light));
                gl_FragColor.xyz += mix(base_color * shadow_tint, base_color, nl) * mix(1, 0.5, shading_sharpness);
            }
        }
        gl_FragColor.a = 1;
    }
}
