
import bpy, mathutils
import gpu
import math

# from.custom_render_engine import MeshDraw, BasePassRendering

DEPTH_ONLY_VERTEX_SHADER = """
uniform mat4 mat_world;
uniform mat4 mat_view_projection;

in vec4 position;

void main()
{
    gl_Position = mat_view_projection * mat_world * position;
}
"""

DEPTH_ONLY_PIXEL_SHADER = """
void main() {}
"""

def frustrum_corners_ws(project, view):
    inv = (project @ view).inverted()
    local_pos = []
    return []

def ortho(left, right, bottom, top, near, far):
    scale = (2.0 / (right - left), 2.0 / (top - bottom), 2.0 / (far - near))
    center = (0.5 * (left + right), 0.5 * (bottom + top), 0.5 * (near + far))
    return (center, scale)

def get_light_matrix(light_object):
    center, scale = ortho(-10, 10, -10, 10, -10, 10)
    mat = mathutils.Matrix.LocRotScale(center, light_object.rotation_euler, scale)
    return mat

class DepthOnlyMeshRendering():
    # def __init__(self, mesh):
    #     super().__init__(mesh)
    #     self.__init__(self) # ???

    def __init__(self, draw):
        self.batch = draw.batch
        self.shader = gpu.types.GPUShader(DEPTH_ONLY_VERTEX_SHADER, DEPTH_ONLY_PIXEL_SHADER)
    
    def draw(self, mat_world, mat_view_projection):
        shader = self.shader
        shader.uniform_float("mat_world", mat_world)
        shader.uniform_float("mat_view_projection", mat_view_projection)
        self.batch.draw(self.shader)

class DirectionalShadowRendering:
    def __init__(self, w = 1024, h = 1024, format="DEPTH_COMPONENT24"):
        self.size = (w, h)
        self.format = format
        self.z = gpu.types.GPUTexture(self.size, format=self.format)
        self.z.clear(format="FLOAT", value=tuple([1.0]))
        self.fb = gpu.types.GPUFrameBuffer(depth_slot=self.z)
    
    def get_depth_texture(self):
        return self.z
    
    def get_light_matrix(self):
        return self.mat_light
    
    def draw_shadowmap(self, light_object, mesh_objects, mesh_draws):
        with self.fb.bind():
            self.fb.clear(depth=1)
            
            for object in mesh_objects:
                draw = DepthOnlyMeshRendering(mesh_draws[object.name])
                self.mat_light = get_light_matrix(light_object)
                draw.draw(object.matrix_world, self.mat_light)