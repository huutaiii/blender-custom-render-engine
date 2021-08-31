
layout(triangles) in;
layout(triangle_strip, max_vertices = 6) out;

in vec4 vertex_color[];
in vec3 world_normal[];
in vec2 texcoord[];

out vec4 color;
out vec3 normal;
out vec2 uv;
out float outline;

uniform mat4 view_matrix;
uniform mat4 projection_matrix;
uniform bool render_outlines;
uniform float outline_width;
const float depth_scale_exponent = 0.75;
uniform int outline_scale_channel;
const float offset_scale = 0.01;

mat4 perspective_matrix = projection_matrix * view_matrix;
vec4 view_location = inverse(view_matrix) * vec4(0, 0, 0, 1);

vec4 offset_vertex(vec4 position, vec3 normal, float vertex_offset_scale)
{
    float view_distance = pow(distance(position.xyz, view_location.xyz), depth_scale_exponent);
    return position + vec4(normal * offset_scale * vertex_offset_scale * outline_width * view_distance, 0);
}

void emit_original_vertex(int index)
{
    gl_Position = perspective_matrix * gl_in[index].gl_Position;
    color = vertex_color[index];
    normal = world_normal[index];
    uv = texcoord[index];
    EmitVertex();
}

void main()
{
    outline = 0;
    emit_original_vertex(0);
    emit_original_vertex(1);
    emit_original_vertex(2);
    EndPrimitive();

    if (render_outlines)
    {
        outline = 1;
        float offset_scale;
        if (outline_scale_channel >= 0)
        {
            gl_Position = perspective_matrix * offset_vertex(gl_in[2].gl_Position, world_normal[2], vertex_color[2][outline_scale_channel]);
            EmitVertex();
            gl_Position = perspective_matrix * offset_vertex(gl_in[1].gl_Position, world_normal[1], vertex_color[1][outline_scale_channel]);
            EmitVertex();
            gl_Position = perspective_matrix * offset_vertex(gl_in[0].gl_Position, world_normal[0], vertex_color[0][outline_scale_channel]);
            EmitVertex();
            EndPrimitive();
        }
        else
        {
            gl_Position = perspective_matrix * offset_vertex(gl_in[2].gl_Position, world_normal[2], 1);
            EmitVertex();
            gl_Position = perspective_matrix * offset_vertex(gl_in[1].gl_Position, world_normal[1], 1);
            EmitVertex();
            gl_Position = perspective_matrix * offset_vertex(gl_in[0].gl_Position, world_normal[0], 1);
            EmitVertex();
            EndPrimitive();
        }
    }
}
