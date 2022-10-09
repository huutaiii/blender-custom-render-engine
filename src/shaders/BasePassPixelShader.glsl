// #version 430 /* inserted automatically by blender */

in vec4 vcolor; // vertex color
in vec3 normal;
in vec3 tangent;
in vec3 view;
in vec2 uv;
in float outline;

layout (location = 0) out vec4 basecolor;
layout (location = 1) out vec4 shadowcolor;
layout (location = 2) out vec4 out_normal;
layout (location = 3) out float out_lighting_mask;

uniform sampler2D tbasecolor;
uniform sampler2D tshadowtint;

void main()
{

    if (outline > 0)
    {
        basecolor = vec4(0, 0, 0, 1);
        shadowcolor = vec4(0, 0, 0, 1);
        out_lighting_mask = 0;
    }
    else
    {
        basecolor = vec4(texture(tbasecolor, uv).rgb, 1);
        shadowcolor = basecolor * vec4(texture(tshadowtint, uv).rgb, 1);
        out_lighting_mask = 1;
    }

    out_normal = vec4(normal, 1);
}
