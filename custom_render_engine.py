"""
Simple Render Engine
++++++++++++++++++++
"""

import bpy
import array
import gpu
from gpu_extras.presets import draw_texture_2d
import bgl
from gpu_extras.batch import batch_for_shader
import numpy as np
from random import random

VERTEX_SHADER = """
uniform mat4 perspective_matrix;
uniform mat4 matrix_world;
in vec3 position;
in vec4 color;
//in vec3 vertex_normal;

varying vec4 vertex_color;

void main()
{
    vec4 pos = vec4(position, 1) * matrix_world * perspective_matrix;
    gl_Position = perspective_matrix * matrix_world * vec4(position, 1);
    //vertex_color = vec3(gl_VertexID / 3 == 0, gl_VertexID / 3 == 1, gl_VertexID / 3 == 2);
    vertex_color = color;
}
"""

PIXEL_SHADER = """
//uniform vec4 color;
varying vec4 vertex_color;

void main()
{
    gl_FragColor = vec4(vertex_color.rgb, 1);
}
"""

class CustomRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "CUSTOM"
    bl_label = "Custom"
    bl_use_preview = True

    # Init is called whenever a new render engine instance is created. Multiple
    # instances may exist at the same time, for example for a viewport and final
    # render.
    def __init__(self):
        self.scene_data = None
        self.draw_data = None
        self.draw_calls = []

    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        pass

    # This is the method called by Blender for both final renders (F12) and
    # small preview for materials, world and lights.
    def render(self, depsgraph):
        scene = depsgraph.scene
        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)

        # Fill the render result with a flat color. The framebuffer is
        # defined as a list of pixels, each pixel itself being a list of
        # R,G,B,A values.
        if self.is_preview:
            color = [0.1, 0.2, 0.1, 1.0]
        else:
            color = [0.2, 0.1, 0.1, 1.0]

        pixel_count = self.size_x * self.size_y
        rect = [color] * pixel_count

        # Here we write the pixel values to the RenderResult
        result = self.begin_result(0, 0, self.size_x, self.size_y)
        layer = result.layers[0].passes["Combined"]
        layer.rect = rect
        self.end_result(result)

    # For viewport renders, this method gets called once at the start and
    # whenever the scene or 3D viewport changes. This method is where data
    # should be read from Blender in the same thread. Typically a render
    # thread will be started to do the work while keeping Blender responsive.
    def view_update(self, context, depsgraph):
        region = context.region
        view3d = context.space_data
        scene = depsgraph.scene

        # Get viewport dimensions
        dimensions = region.width, region.height

#        self.draw_calls = {}
        
        if not self.scene_data:
            # First time initialization
            self.scene_data = []
            first_time = True

            # Loop over all datablocks used in the scene.
            for datablock in depsgraph.ids:
#                if isinstance(datablock, bpy.types.Mesh):
#                    self.draw_calls[datablock.name] = MeshDrawData(datablock)
                pass
        else:
            first_time = False

            # Test which datablocks changed
            for update in depsgraph.updates:
                print("Datablock updated: ", update.id.name)
#                datablock = update.id
#                if isinstance(datablock, bpy.types.Mesh):
#                    self.draw_calls[datablock.name] = MeshDrawData(datablock)

            # Test if any material was added, removed or changed.
            if depsgraph.id_type_updated('MATERIAL'):
                print("Materials updated")

        # Loop over all object instances in the scene.
        if first_time or depsgraph.id_type_updated('OBJECT'):
            pass
            # self.draw_calls = {}
            for draw in self.draw_calls:
                self.draw_calls.remove(draw)
            for instance in depsgraph.object_instances:
                object = instance.object
                if object.type == 'MESH':
                    print("instancing draw: " + object.name)
                    mesh = depsgraph.id_eval_get(object.data) # mesh = object.data
                    matrix_world = object.matrix_world
                    draw = GpuDraw(mesh, matrix_world)
                    draw.object_name = object.name
                    self.draw_calls.append(draw)

            
    # For viewport renders, this method is called whenever Blender redraws
    # the 3D viewport. The renderer is expected to quickly draw the render
    # with OpenGL, and not perform other expensive work.
    # Blender will draw overlays for selection and editing on top of the
    # rendered image automatically.
    def view_draw(self, context, depsgraph):
        region = context.region
        scene = depsgraph.scene

#        # Get viewport dimensions
        # dimensions = region.width, region.height

        bgl.glClearColor(0, 0, 0, 1)
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT | bgl.GL_DEPTH_BUFFER_BIT | bgl.GL_STENCIL_BUFFER_BIT)
        # Bind (fragment) shader that converts from scene linear to display space,
        # self.bind_display_space_shader(scene)
        # gpu.state.blend_set('ALPHA')
        # gpu.state.depth_mask_set(True)
        # gpu.state.depth_test_set('LESS_EQUAL')
        # gpu.state.face_culling_set('BACK')
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        # bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_LINE)
        # bgl.glEnable(bgl.GL_CULL_FACE)

        for draw in self.draw_calls:
            # print("drawing:", draw.object_name, draw.elem_count, draw.transform)
            draw.draw(context.region_data.perspective_matrix)

        # bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

        # self.unbind_display_space_shader()
        # gpu.state.blend_set('NONE')
        # gpu.state.depth_test_set('NONE')
        # gpu.state.depth_mask_set(False)
        
class MeshDrawData:
    def __init__(self, mesh, matrix_world):
        mesh.calc_loop_triangles()
        # mesh.calc_tangents()
        self.transform = matrix_world

        vertices = np.empty((len(mesh.loops), 3), dtype=np.float32)
        color = np.empty((len(mesh.loops), 4), dtype=np.float32)
        indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.uintc)
        
        for  i in range(len(mesh.loops)):
            loop = mesh.loops[i]
            vertices[i] = mesh.vertices[loop.vertex_index].co
            color[i] = [random(), random(), random(), 1]
        mesh.loop_triangles.foreach_get("loops", np.reshape(indices, len(mesh.loop_triangles) * 3))

        self.vertex_count = len(vertices)
        self.elem_count = len(indices.flatten())
        print(self.vertex_count, " ", self.elem_count)

        vertices = bgl.Buffer(bgl.GL_FLOAT, [len(vertices), 3], vertices)
        color = bgl.Buffer(bgl.GL_FLOAT, [len(color), 4], color)
        indices = bgl.Buffer(bgl.GL_INT, [len(indices), 3], indices)
        
        vertex_shader = bgl.glCreateShader(bgl.GL_VERTEX_SHADER)
        bgl.glShaderSource(vertex_shader, VERTEX_SHADER)
        bgl.glCompileShader(vertex_shader)
        pixel_shader = bgl.glCreateShader(bgl.GL_FRAGMENT_SHADER)
        bgl.glShaderSource(pixel_shader, PIXEL_SHADER)
        bgl.glCompileShader(pixel_shader)
        self.program = bgl.glCreateProgram()
        bgl.glAttachShader(self.program, vertex_shader)
        bgl.glAttachShader(self.program, pixel_shader)
        bgl.glLinkProgram(self.program)
            
        self.vertex_array = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGenVertexArrays(1, self.vertex_array)
        bgl.glBindVertexArray(self.vertex_array[0])
        
        self.vertex_buffer = bgl.Buffer(bgl.GL_INT, 2)
        bgl.glGenBuffers(2, self.vertex_buffer)
        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, self.vertex_buffer[0])
        bgl.glBufferData(bgl.GL_ARRAY_BUFFER, len(vertices), vertices, bgl.GL_STATIC_DRAW)
        position_attrib_location = bgl.glGetAttribLocation(self.program, "position")
        bgl.glVertexAttribPointer(position_attrib_location, 3, bgl.GL_FLOAT, bgl.GL_FALSE, 0, None)
        bgl.glEnableVertexAttribArray(position_attrib_location)
        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, self.vertex_buffer[1])
        bgl.glBufferData(bgl.GL_ARRAY_BUFFER, len(color), color, bgl.GL_STATIC_DRAW)
        color_attrib_location = bgl.glGetAttribLocation(self.program, "color")
        bgl.glVertexAttribPointer(color_attrib_location, 4, bgl.GL_FLOAT, bgl.GL_FALSE, 0, None)
        bgl.glEnableVertexAttribArray(color_attrib_location)
        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, 0)

        self.index_buffer = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGenBuffers(1, self.index_buffer)
        bgl.glBindBuffer(bgl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer[0])
        bgl.glBufferData(bgl.GL_ELEMENT_ARRAY_BUFFER, len(indices), indices, bgl.GL_STATIC_DRAW)
        
        bgl.glBindVertexArray(0)
        bgl.glBindBuffer(bgl.GL_ELEMENT_ARRAY_BUFFER, 0)

        bgl.glDeleteShader(vertex_shader)
        bgl.glDeleteShader(pixel_shader)
    
    def __del__(self):
        bgl.glDeleteProgram(self.program)
        bgl.glDeleteBuffers(2, self.vertex_buffer)
        bgl.glDeleteBuffers(1, self.index_buffer)
        bgl.glDeleteVertexArrays(1, self.vertex_array)

    def draw(self, region_data):
        bgl.glUseProgram(self.program)
        bgl.glBindVertexArray(self.vertex_array[0])
        
        transform_location = bgl.glGetUniformLocation(self.program, "matrix_world")
        transform_buffer = bgl.Buffer(bgl.GL_FLOAT, [4, 4], self.transform)
        bgl.glUniformMatrix4fv(transform_location, 1, bgl.GL_FALSE, transform_buffer)
        projection_location = bgl.glGetUniformLocation(self.program, "perspective_matrix")
        projection_buffer = bgl.Buffer(bgl.GL_FLOAT, [4, 4], region_data.perspective_matrix)
        bgl.glUniformMatrix4fv(projection_location, 1, bgl.GL_FALSE, projection_buffer)
        bgl.glDrawElements(bgl.GL_TRIANGLES, self.elem_count, bgl.GL_UNSIGNED_INT, 0)
        # bgl.glDrawArrays(bgl.GL_TRIANGLES, 0, self.vertex_count)
        
        bgl.glUseProgram(0)
        bgl.glBindVertexArray(0)

class GpuDraw:
    def __init__(self, mesh, transform):
        self.transform = transform
        mesh.calc_loop_triangles()

        vertices = np.empty((len(mesh.loops), 3), dtype=np.float32)
        color = np.empty((len(mesh.loops), 4), dtype=np.float32)
        indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.uintc)
        
        for  i in range(len(mesh.loops)):
            loop = mesh.loops[i]
            vertices[i] = mesh.vertices[loop.vertex_index].co
            color[i] = [1, 1, 1, 1]
        mesh.loop_triangles.foreach_get("loops", np.reshape(indices, len(mesh.loop_triangles) * 3))

        # fmt = gpu.types.GPUVertFormat()
        # fmt.attr_add(id="position", comp_type='F32', len=3, fetch_mode="FLOAT")
        # fmt.attr_add(id="color", comp_type='F32', len=4, fetch_mode="FLOAT")

        # vbo = gpu.types.GPUVertBuf(len=len(vertices), format=fmt)
        # vbo.attr_fill(id="position", data=vertices)
        # vbo.attr_fill(id="color", data=color)

        # ibo = gpu.types.GPUIndexBuf(types="TRIS", seq=indices)

        self.shader = gpu.types.GPUShader(VERTEX_SHADER, PIXEL_SHADER)
        self.batch = batch_for_shader(self.shader, 'TRIS', {"position": vertices, "color": color}, indices=indices)
    
    def draw(self, perspective_matrix):
        self.shader.bind()
        self.shader.uniform_float("matrix_world", self.transform)
        self.shader.uniform_float("perspective_matrix", perspective_matrix)
        self.batch.draw(self.shader)

class CustomDrawData:
    def __init__(self, dimensions):
        # Generate dummy float image buffer
        self.dimensions = dimensions
        width, height = dimensions

        pixels = [0.1, 0.2, 0.1, 0.4] * width * height
        pixels = bgl.Buffer(bgl.GL_FLOAT, width * height * 4, pixels)

        # Generate texture
        self.texture = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGenTextures(1, self.texture)
        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, self.texture[0])
        bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA16F, width, height, 0, bgl.GL_RGBA, bgl.GL_FLOAT, pixels)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MAG_FILTER, bgl.GL_LINEAR)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)

        # Bind shader that converts from scene linear to display space,
        # use the scene's color management settings.
        shader_program = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGetIntegerv(bgl.GL_CURRENT_PROGRAM, shader_program)

        # Generate vertex array
        self.vertex_array = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGenVertexArrays(1, self.vertex_array)
        bgl.glBindVertexArray(self.vertex_array[0])

        texturecoord_location = bgl.glGetAttribLocation(shader_program[0], "texCoord")
        position_location = bgl.glGetAttribLocation(shader_program[0], "pos")

        bgl.glEnableVertexAttribArray(texturecoord_location)
        bgl.glEnableVertexAttribArray(position_location)

        # Generate geometry buffers for drawing textured quad
        position = [0.0, 0.0, width, 0.0, width, height, 0.0, height]
        position = bgl.Buffer(bgl.GL_FLOAT, len(position), position)
        texcoord = [0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
        texcoord = bgl.Buffer(bgl.GL_FLOAT, len(texcoord), texcoord)

        self.vertex_buffer = bgl.Buffer(bgl.GL_INT, 2)

        bgl.glGenBuffers(2, self.vertex_buffer)
        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, self.vertex_buffer[0])
        bgl.glBufferData(bgl.GL_ARRAY_BUFFER, 32, position, bgl.GL_STATIC_DRAW)
        bgl.glVertexAttribPointer(position_location, 2, bgl.GL_FLOAT, bgl.GL_FALSE, 0, None)

        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, self.vertex_buffer[1])
        bgl.glBufferData(bgl.GL_ARRAY_BUFFER, 32, texcoord, bgl.GL_STATIC_DRAW)
        bgl.glVertexAttribPointer(texturecoord_location, 2, bgl.GL_FLOAT, bgl.GL_FALSE, 0, None)

        bgl.glBindBuffer(bgl.GL_ARRAY_BUFFER, 0)
        bgl.glBindVertexArray(0)

    def __del__(self):
        bgl.glDeleteBuffers(2, self.vertex_buffer)
        bgl.glDeleteVertexArrays(1, self.vertex_array)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
        bgl.glDeleteTextures(1, self.texture)

    def draw(self):
        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, self.texture[0])
        bgl.glBindVertexArray(self.vertex_array[0])
        bgl.glDrawArrays(bgl.GL_TRIANGLE_FAN, 0, 4)
        bgl.glBindVertexArray(0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)


# RenderEngines also need to tell UI Panels that they are compatible with.
# We recommend to enable all panels marked as BLENDER_RENDER, and then
# exclude any panels that are replaced by custom panels registered by the
# render engine, or that are not supported.
def get_panels():
    exclude_panels = {
        'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes',
    }

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)

    return panels


def register():
    # Register the RenderEngine
    bpy.utils.register_class(CustomRenderEngine)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('CUSTOM')


def unregister():
    bpy.utils.unregister_class(CustomRenderEngine)

    for panel in get_panels():
        if 'CUSTOM' in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove('CUSTOM')


if __name__ == "__main__":
    register()
