
in vec4 color;
in vec3 normal;
in vec2 uv;
in float outline;

uniform mat4 directional_lights;
uniform float shading_sharpness;
uniform bool use_texture;
uniform sampler2D basecolor;
uniform vec4 world_color;

void main()
{
    if (outline > 0)
    {
        gl_FragColor = vec4(0, 0, 0, 1);
    } 
    else
    {
        vec3 base_color = use_texture ? texture(basecolor, uv).xyz : vec3(1, 1, 1);
        gl_FragColor.xyz = base_color * world_color.xyz;
        for (int i = 0; i <= 3; ++i)
        {
            vec3 light = directional_lights[i].xyz;
            float nl = smoothstep(0, 1 - shading_sharpness, dot(normal, light));
            gl_FragColor.xyz += base_color * nl;
        }
        gl_FragColor.a = 1;
    }
}
