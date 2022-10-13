// #version 430

in vec3 position;
in vec3 normal;
in vec3 tangent;
in float bitangent_sign;
in vec4 color;
in vec2 uv;

out vec4 vertex_color;
out vec3 world_normal;
out vec3 world_tangent;
out float tangent_sign;
out vec2 texcoord;

uniform mat4 matrix_world;

void main()
{
    gl_Position = matrix_world * vec4(position, 1);
    world_normal = normalize((matrix_world * vec4(normal, 0)).xyz);
    world_tangent = normalize((matrix_world * vec4(tangent, 0)).xyz);
    tangent_sign = bitangent_sign;
    vertex_color = color;
    texcoord = uv;
}
