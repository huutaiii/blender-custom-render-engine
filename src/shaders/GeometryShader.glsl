
layout(triangles) in;
layout(triangle_strip, max_vertices = 6) out;

in vec4 vertex_color[];
in vec3 world_normal[];
in vec3 world_tangent[];
in float tangent_sign[];
in vec2 texcoord[];

out vec3 normal;
out vec3 tangent;
out vec4 color;
out vec2 uv;
out vec3 view;
out float outline;

uniform mat4 view_matrix;
uniform mat4 projection_matrix;

uniform bool render_outlines;
uniform float outline_width;
uniform bool use_vertexcolor_alpha;
uniform bool use_vertexcolor_rgb;
uniform float depth_scale_exponent;

const float OFFSET_SCALE = 0.01;

mat4 perspective_matrix = projection_matrix * view_matrix;
vec4 view_location = inverse(view_matrix) * vec4(0, 0, 0, 1);

vec4 offset_vertex(vec4 position, vec3 normal, vec3 tangent, float tangent_sign, vec4 vertex_color)
{
    vec3 world_normal = normal;
    if (use_vertexcolor_rgb)
    {
        vec3 bitangent = normalize(cross(normal, tangent) * tangent_sign);
        mat3 tangent_space = mat3(tangent, bitangent, normal);
        world_normal = tangent_space * (vertex_color.rgb * 2 - 1);
    }
    float view_distance = pow(distance(position.xyz, view_location.xyz), depth_scale_exponent);
    // return position + vec4(normal * offset_scale * vertex_offset_scale * outline_width * view_distance, 0);
    float vertex_offset_scale = use_vertexcolor_alpha ? vertex_color.a : 1;
    float offset = OFFSET_SCALE * vertex_offset_scale * outline_width * view_distance;
    vec3 offset_z = world_normal * offset;
    return position + vec4(offset_z, 0);
}

void emit_original_vertex(int index)
{
    gl_Position = perspective_matrix * gl_in[index].gl_Position;
    normal = world_normal[index];
    tangent = world_tangent[index];
    color = vertex_color[index];
    uv = texcoord[index];
    view = normalize((view_location - gl_in[index].gl_Position).xyz);
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
        gl_Position = perspective_matrix * offset_vertex(gl_in[2].gl_Position, world_normal[2], world_tangent[2], tangent_sign[2], vertex_color[2]);
        EmitVertex();
        gl_Position = perspective_matrix * offset_vertex(gl_in[1].gl_Position, world_normal[1], world_tangent[1], tangent_sign[1], vertex_color[1]);
        EmitVertex();
        gl_Position = perspective_matrix * offset_vertex(gl_in[0].gl_Position, world_normal[0], world_tangent[0], tangent_sign[0], vertex_color[0]);
        EmitVertex();
        EndPrimitive();
    }
}
