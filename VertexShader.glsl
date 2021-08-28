
in vec3 position;
in vec3 normal;
in vec4 color;

out vec4 vertex_color;
out vec3 world_normal;

uniform mat4 matrix_world;

void main()
{
    gl_Position = matrix_world * vec4(position, 1);
    world_normal = (matrix_world * vec4(normal, 0)).xyz;
    vertex_color = color;
}
