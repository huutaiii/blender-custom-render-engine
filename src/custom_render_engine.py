"""
Simple Render Engine
++++++++++++++++++++
"""

import math
import os
import sys

def get_path(file):
    delimiter = None
    if os.name == 'nt':
        delimiter = '\\'
    if os.name == 'posix':
        delimiter = '/'
    if not delimiter:
        raise RuntimeError("Platform not supported")
    names = __file__.split(delimiter)
    path = delimiter.join(names[:len(names)-1]) + delimiter
    path += file.replace('/', delimiter)
    return path

sys.path.append(get_path(""))

import operators

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_texture_2d
import mathutils
import numpy as np

bl_info = {
    "name": "Custom Render Engine",
    # "description": "Single line explaining what this script exactly does.",
    "author": "huutai",
    "version": (0, 1),
    "blender": (3, 3, 0),
    "category": "Render",
}

VERTEX_SHADER = open(get_path("shaders/VertexShader.glsl")).read()
GEOMETRY_SHADER = open(get_path("shaders/GeometryShader.glsl")).read()
PIXEL_SHADER = open(get_path("shaders/PixelShader.glsl")).read()

VERTEX_2D = """
    in vec2 pos;
    out vec2 uv;

    void main()
    {
        uv = pos;
        gl_Position = vec4(pos * 2 - 1, 0, 1);
    }
"""

PIXEL_2D = """
    uniform sampler2D image;
    in vec2 uv;
    out vec4 color;

    void main()
    {
        color = texture(image, uv);
        if (color.a == 0) discard;
    }
"""

PIXEL_AVG = """
    uniform sampler2D image;
    uniform ivec2 view_size;
    uniform ivec2 buffer_size;

    in vec2 uv;

    out vec4 color;

    void main()
    {
        vec4 tex = texture(image, uv);
        if (length(view_size) < length(buffer_size))
        {
            int count = 0;
            vec4 acc = vec4(0);
            ivec2 scale = view_size / buffer_size;
            ivec2 ipos = ivec2(round(uv * buffer_size));
            ivec2 end = ipos + scale;
            for (; ipos.x <= end.x; ++ipos.x)
            {
                for (; ipos.y <= end.y; ++ipos.y)
                {
                    vec4 texel = texelFetch(image, ipos, 0);
                    acc += texel;
                    ++count;
                }
            }
            acc /= count;
            tex = acc;
        }
        color = tex;
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
        self.draw_calls = {}
        self.lights = []
        self.mesh_objects = []

    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        pass

    def get_settings(self, context):
        return context.scene.custom_render_engine

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

        if not self.scene_data:
            # First time initialization
            print("Initializing renderer", flush=True)
            self.scene_data = [0]
            first_time = True

            # Loop over all datablocks used in the scene.
            for datablock in depsgraph.ids:
                if isinstance(datablock, bpy.types.Object) and datablock.type == 'MESH':
                    # print(datablock.type, " ", datablock.name, flush=True)
                    draw = MeshDraw(datablock.data, self.get_settings(context))
                    draw.object = datablock
                    self.draw_calls[datablock.name] = draw
                pass
        else:
            first_time = False

            # Test which datablocks changed
            for update in depsgraph.updates:
                # print("Datablock updated: ", update.id.name, flush=True)
                datablock = update.id
                if isinstance(datablock, bpy.types.Object) \
                and datablock.type == 'MESH' and update.is_updated_geometry:
                    # print("mesh updated: ", datablock.name, flush=True)
                    # del self.draw_calls[datablock.name]
                    draw = MeshDraw(datablock.data, self.get_settings(context))
                    draw.object = datablock
                    self.draw_calls[datablock.name] = draw

            # Test if any material was added, removed or changed.
            if depsgraph.id_type_updated('MATERIAL'):
                # print("Materials updated")
                pass

        # Loop over all object instances in the scene.
        if first_time or depsgraph.id_type_updated('OBJECT'):
            pass
            self.mesh_objects = []
            for instance in depsgraph.object_instances:
                object = instance.object
                if object.type == 'MESH':
                    self.mesh_objects.append(object)
            self.lights = []
            # for light in self.lights:
            #     self.lights.remove(light)
            for instance in depsgraph.object_instances:
                object = instance.object
                if object.type == 'LIGHT':
                    if object.data.type == 'SUN':
                        # print("light: ", object.name)
                        light_direction = mathutils.Vector((0, 0, 1))
                        light_direction.rotate(object.matrix_world.decompose()[1])
                        light = light_direction.to_4d()
                        light.w = object.data.energy
                        self.lights.append(light)


    # For viewport renders, this method is called whenever Blender redraws
    # the 3D viewport. The renderer is expected to quickly draw the render
    # with OpenGL, and not perform other expensive work.
    # Blender will draw overlays for selection and editing on top of the
    # rendered image automatically.
    def view_draw(self, context, depsgraph):
        
        region = context.region
        scene = depsgraph.scene

        # Get viewport dimensions
        dimensions = region.width, region.height

        settings = self.get_settings(context)

        fb = gpu.state.active_framebuffer_get() # it's framebuffer_active_get in the api docs wtf?
        x, y, w, h = gpu.state.viewport_get()

        offscr_scale = settings.backbuffer_scale
        # if offscr_scale > 1:
        #     offscr_scale = math.floor(offscr_scale)
        rgb = gpu.types.GPUTexture((math.floor(w * offscr_scale), math.floor(h * offscr_scale)), format="RGBA16")
        z = gpu.types.GPUTexture((math.floor(w * offscr_scale), math.floor(h * offscr_scale)), format="DEPTH_COMPONENT24")
        rb = gpu.types.GPUFrameBuffer(depth_slot=z, color_slots=(rgb))

        with rb.bind():

            if settings.world_color_clear:
                color = settings.world_color
            else:
                color = None
            gpu.state.active_framebuffer_get().clear(color=color, depth=1)

            # Bind (fragment) shader that converts from scene linear to display space,
            # self.bind_display_space_shader(scene)

            gpu.state.depth_test_set("LESS")
            gpu.state.depth_mask_set(True)
            gpu.state.face_culling_set("BACK")

            for object in self.mesh_objects:
                draw = self.draw_calls[object.name]
                draw.draw(object.matrix_world, context.region_data, self.lights, settings)
            # for key, draw in self.draw_calls.items():
            #     print(draw.object.name, " ", draw.object.hide_viewport, flush=True)
            #     draw.draw(draw.object.matrix_world, context.region_data, self.lights, settings)


            # self.unbind_display_space_shader()

        with fb.bind():
            gpu.state.depth_test_set("LESS")
            gpu.state.depth_mask_set(True)
            gpu.state.face_culling_set("NONE")
            
            coords = ((0, 0), (1, 0), (1, 1), (0, 1))
            shader = gpu.types.GPUShader(VERTEX_2D, PIXEL_2D)
            vbo = gpu.types.GPUVertBuf(shader.format_calc(), 4)
            vbo.attr_fill("pos", coords)
            batch = gpu.types.GPUBatch(type="TRI_FAN", buf=vbo)
            shader.bind()
            shader.uniform_sampler("image", rgb)
            # shader.uniform_int("view_size", (w, h))
            # shader.uniform_int("buffer_size", (rgb.width, rgb.height))
            batch.draw(shader)
            
class MeshDraw:
    def __init__(self, mesh, settings):
        # print("AAAAAAAAAAAAAAA", mesh, flush=True)
        mesh.calc_loop_triangles()
        try:
            mesh.calc_tangents()
        except:
            pass

        vertices = np.empty((len(mesh.loops), 3), dtype=np.float32)
        color = np.full((len(mesh.loops), 4), [0.5, 0.5, 1, 1], dtype=np.float32)
        normals = np.empty((len(mesh.loops), 3), dtype=np.float32)
        tangents = np.empty((len(mesh.loops), 3), dtype=np.float32)
        bitangent_signs = np.empty(len(mesh.loops), dtype=np.half)
        uvs = np.zeros((len(mesh.loops), 2), dtype=np.float32)
        indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.uintc)

        coords = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        mesh.vertices.foreach_get("co", np.reshape(coords, len(mesh.vertices) * 3))
        loop_vertices = np.empty(len(mesh.loops), dtype=np.int)
        mesh.loops.foreach_get("vertex_index", loop_vertices)
        vertices = coords[loop_vertices]

        mesh.loops.foreach_get("normal", np.reshape(normals, len(mesh.loops) * 3))
        mesh.loops.foreach_get("tangent", np.reshape(tangents, len(mesh.loops) * 3))
        mesh.loops.foreach_get("bitangent_sign", bitangent_signs)
        bitangent_signs = np.negative(bitangent_signs)
        if mesh.uv_layers.active:
            mesh.uv_layers.active.data.foreach_get("uv", np.reshape(uvs, len(mesh.loops) * 2))
        if mesh.vertex_colors.active:
            mesh.vertex_colors.active.data.foreach_get("color", np.reshape(color, len(mesh.loops) * 4))

        mesh.loop_triangles.foreach_get("loops", np.reshape(indices, len(mesh.loop_triangles) * 3))

        # fmt = gpu.types.GPUVertFormat()
        # fmt.attr_add(id="position", comp_type='F32', len=3, fetch_mode="FLOAT")
        # fmt.attr_add(id="color", comp_type='F32', len=4, fetch_mode="FLOAT")

        # vbo = gpu.types.GPUVertBuf(len=len(vertices), format=fmt)
        # vbo.attr_fill(id="position", data=vertices)
        # vbo.attr_fill(id="color", data=color)

        # ibo = gpu.types.GPUIndexBuf(types="TRIS", seq=indices)

        self.shader = gpu.types.GPUShader(VERTEX_SHADER, PIXEL_SHADER, geocode=GEOMETRY_SHADER)
        self.batch = batch_for_shader(self.shader, 'TRIS', {"position": vertices, "normal": normals, "tangent": tangents, "bitangent_sign": bitangent_signs, "uv": uvs, "color": color}, indices=indices)


    def draw(self, transform, region_data, lights, settings):
        def min(a, b):
            if a > b:
                return b
            else:
                return a

        self.shader.bind()
        try:
            self.shader.uniform_float("matrix_world", transform)
            # self.shader.uniform_float("perspective_matrix", perspective_matrix)
            self.shader.uniform_float("view_matrix", region_data.view_matrix)
            self.shader.uniform_float("projection_matrix", region_data.window_matrix)
            packed_lights = mathutils.Matrix.Diagonal(mathutils.Vector((0, 0, 0, 0)))
            for i in range(min(len(lights), 4)):
                packed_lights[i].xyz = lights[i].xyz # direction
                packed_lights[i].w = lights[i].w # strength
            self.shader.uniform_float("directional_lights", packed_lights.transposed())
            self.shader.uniform_bool("render_outlines", [settings.enable_outline])
            self.shader.uniform_float("shading_sharpness", settings.shading_sharpness)
            self.shader.uniform_float("fresnel_fac", settings.fresnel_fac)
            self.shader.uniform_float("world_color", settings.world_color)

            self.shader.uniform_float("outline_width", settings.outline_width)
            self.shader.uniform_float("depth_scale_exponent", settings.outline_depth_exponent)
            self.shader.uniform_bool("use_vertexcolor_alpha", [settings.use_vertexcolor_alpha])
            self.shader.uniform_bool("use_vertexcolor_rgb", [settings.use_vertexcolor_rgb])

            try:
                if settings.basecolor_texture:
                    tbasecolor = gpu.texture.from_image(bpy.data.images[settings.basecolor_texture])
                else:
                    tbasecolor = gpu.types.GPUTexture((1, 1))
                    tbasecolor.clear(format="FLOAT", value=(0.5, 0.5, 0.5, 1))
                self.shader.uniform_sampler("tbasecolor", tbasecolor)
                
                if settings.shadowtint_texture:
                    tshadowtint = gpu.texture.from_image(bpy.data.images[settings.basecolor_texture])
                else:
                    tshadowtint = gpu.types.GPUTexture((1, 1))
                    tshadowtint.clear(format="FLOAT", value=(0, 0, 0, 1))
                self.shader.uniform_sampler("tshadowtint", tshadowtint)

            except KeyError:
                pass
        except ValueError:
            pass
        self.batch.draw(self.shader)

class CustomRenderEngineSettings(bpy.types.PropertyGroup):
    backbuffer_scale: bpy.props.FloatProperty(name="Backbuffer Scale", default=1.0, min=0.1, max=10)

    enable_outline: bpy.props.BoolProperty(name="Render Outlines", default=True, options=set())
    outline_width: bpy.props.FloatProperty(name="Outline Width", default=1, min=0, soft_max=10, options=set())
    outline_depth_exponent: bpy.props.FloatProperty(name="Outline Depth Scale Exponent", default=0.75, min=0, max=1, options=set())
    shading_sharpness: bpy.props.FloatProperty(name="Shading Sharpness", default=1, subtype='FACTOR', min=0, max=1, options=set())
    fresnel_fac: bpy.props.FloatProperty(name="Fresnel Factor", default=0.5, min=0, max=1)
    use_vertexcolor_alpha: bpy.props.BoolProperty(name="Use Vertex Color Alpha", default=False, options=set(), description="Used as offset scaling")
    use_vertexcolor_rgb: bpy.props.BoolProperty(name="Use Vertex Color RGB", default=False, options=set(), description="Used as normal map for outline")

    # TODO: Materials
    basecolor_texture: bpy.props.StringProperty(name="Base Color")
    shadowtint_texture: bpy.props.StringProperty(name="Shadow Tint")

    world_color: bpy.props.FloatVectorProperty(name="World Color", size=4, default=(0.1, 0.1, 0.1, 1), subtype='COLOR', min=0, max=1, options=set())
    world_color_clear: bpy.props.BoolProperty(name="World Color Clear", default=False, options=set())

    def get_channel_index(c):
        return {
            'R': 0,
            'G': 1,
            'B': 2,
            'A': 3,
            "0": -1
        }[c]

class CustomRenderEnginePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_CustomRenderEngine"
    bl_label = "Custom Render Engine Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    # COMPAT_ENGINES = {'CUSTOM'}

    @classmethod
    def poll(cls, context):
        return context.engine == "CUSTOM"

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = True
        layout.use_property_split = True
        settings = context.scene.custom_render_engine
        layout.prop(settings, "backbuffer_scale")
        layout.prop(settings, "enable_outline")
        layout.prop(settings, "outline_width")
        layout.prop(settings, "outline_depth_exponent")
        layout.prop(settings, "use_vertexcolor_alpha")
        layout.prop(settings, "use_vertexcolor_rgb")
        layout.prop_search(settings, "basecolor_texture", bpy.data, "images")
        layout.prop_search(settings, "shadowtint_texture", bpy.data, "images")
        layout.prop(settings, "world_color")
        layout.prop(settings, "world_color_clear")
        layout.prop(settings, "shading_sharpness")
        layout.prop(settings, "fresnel_fac")

# expose light properties
class CustomRenderEngineLightPanel(bpy.types.Panel):
    # bl_idname = "RENDER_PT_CustomRenderEngineLight"
    bl_label = "Light"
    bl_context = "data"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"

    @classmethod
    def poll(cls, context):
        return context.engine == "CUSTOM"
    
    def draw(self, context):
        # layout = self.layout
        light = context.light
        col = self.layout.column()
        col.prop(light, "energy")

        if (light.type == "SUN"):
            col.prop(light, "angle")


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

classes = [
    CustomRenderEngine,
    CustomRenderEngineSettings,
    CustomRenderEnginePanel,
    CustomRenderEngineLightPanel
]

def register():
    # Register the RenderEngine
    for c in classes:
        bpy.utils.register_class(c)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('CUSTOM')

    bpy.types.Scene.custom_render_engine = bpy.props.PointerProperty(type=CustomRenderEngineSettings)

    operators.register()


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    for panel in get_panels():
        if 'CUSTOM' in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove('CUSTOM')

    operators.unregister()


if __name__ == "__main__":
    register()
