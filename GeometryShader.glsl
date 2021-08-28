
layout(triangles) in;
layout(triangle_strip, max_vertices = 6) out;

in vec4 vertex_color[];
in vec3 world_normal[];

out vec4 color;
out vec3 normal;
out float outline;

//uniform mat4 perspective_matrix;
uniform mat4 view_matrix;
uniform mat4 projection_matrix;
const float offset_scale = 0.002;

vec4 offset_vertex(vec4 position, vec3 normal, vec4 view_location)
{
    float distance = length((position - view_location).xyz);
    return position + vec4(normal * offset_scale * pow(distance, 1.1), 0);
}

void main()
{
    mat4 perspective_matrix = projection_matrix * view_matrix;

    outline = 0;
    gl_Position = perspective_matrix * gl_in[0].gl_Position;
    color = vertex_color[0];
    normal = world_normal[0];
    EmitVertex();
    gl_Position = perspective_matrix * gl_in[1].gl_Position;
    color = vertex_color[1];
    normal = world_normal[1];
    EmitVertex();
    gl_Position = perspective_matrix * gl_in[2].gl_Position;
    color = vertex_color[2];
    normal = world_normal[2];
    EmitVertex();
    EndPrimitive();

    outline = 1;
    vec4 view_location = view_matrix[3];
    gl_Position = perspective_matrix * offset_vertex(gl_in[2].gl_Position, world_normal[2], view_location);
    EmitVertex();
    gl_Position = perspective_matrix * offset_vertex(gl_in[1].gl_Position, world_normal[1], view_location);
    EmitVertex();
    gl_Position = perspective_matrix * offset_vertex(gl_in[0].gl_Position, world_normal[0], view_location);
    EmitVertex();
    EndPrimitive();
}
