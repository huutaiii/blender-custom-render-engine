"""
Simple Render Engine
++++++++++++++++++++
"""

import math

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import mathutils
import numpy as np

# from . import material
# print(material.__name__, flush=True)

VERTEX_SHADER = open("shaders/VertexShader.glsl").read()
GEOMETRY_SHADER = open("shaders/GeometryShader.glsl").read()
PIXEL_SHADER = open("shaders/PixelShader.glsl").read()

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
    uniform sampler2D depth;
    in vec2 uv;
    out vec4 color;

    void main()
    {
        color = finalize_color(texture(image, uv));
        gl_FragDepth = texture(depth, uv).x;
    }
"""

PIXEL_RGBL = """
    uniform sampler2D image;
    in vec2 uv;
    out vec4 color;

    void main()
    {
        color = texture(image, uv);
        color.a = dot(color.rgb, vec3(0.3, 0.59, 0.11));
    }
"""

PIXEL_FXAA = """
    uniform sampler2D image;
    uniform sampler2D depth;
    in vec2 uv;
    out vec4 color;

    uniform vec2 invScreenSize;

    FXAA_HEADER

    void main()
    {
    #if USE_FXAA
        color = FxaaPixelShader(
            uv,
            vec4(0.0),
            image,
            image,
            image,
            invScreenSize,
            vec4(0.0),
            vec4(0.0),
            vec4(0.0),
            0.75,
            0.166,
            0.0833,
            0.0,
            0.0,
            0.0,
            vec4(0.0));
    #else
        color = texture(image, uv);
    #endif
        color.a = 1;
        gl_FragDepth = texture(depth, uv).x;
    }
"""

PIXEL_DEFERRED_WORLDPOS = """
    uniform sampler2D image; // unused
    uniform sampler2D depth;
    in vec2 uv;
    out vec4 color;
    //uniform mat4 mat_view;
    //uniform mat4 mat_projection;
    uniform mat4 mat_view_projection;

    vec3 ScreenToWorldPos()
    {
        vec4 pos;
        pos.w = 1;
        pos.xy = uv * 2 - 1;
        pos.z = texture(depth, uv).r * 2 - 1;
        pos = inverse(mat_view_projection) * pos;
        pos /= pos.w;
        return pos.xyz;
    }

    void main()
    {
        vec3 pos = ScreenToWorldPos();
        color = vec4(fract(pos), 1);
        gl_FragDepth = texture(depth, uv).x;
    }
"""

# PIXEL_AVG = """
#     uniform sampler2D image;
#     uniform sampler2D depth;
#     uniform ivec2 view_size;
#     uniform ivec2 buffer_size;

#     in vec2 uv;

#     out vec4 color;

#     void main()
#     {
#         vec4 tex = texture(image, uv);
#         if (length(view_size) < length(buffer_size))
#         {
#             int count = 0;
#             vec4 acc = vec4(0);
#             ivec2 scale = view_size / buffer_size;
#             ivec2 ipos = ivec2(round(uv * buffer_size));
#             ivec2 end = ipos + scale;
#             for (; ipos.x <= end.x; ++ipos.x)
#             {
#                 for (; ipos.y <= end.y; ++ipos.y)
#                 {
#                     vec4 texel = texelFetch(image, ipos, 0);
#                     acc += texel;
#                     ++count;
#                 }
#             }
#             acc /= count;
#             tex = acc;
#         }
#         color = tex;
#     }
# """

PIXEL_SCENE_LIGHTING = """
    uniform sampler2D tbasecolor;
    uniform sampler2D tmask;
    in vec2 uv;

    out vec4 color;

    uniform vec4 scene_color;

    void main()
    {
        vec4 tex = texture(tbasecolor, uv);
        float mask = texture(tmask, uv).r;
    #if BACKGROUND_COLOR
        color.rgb = mix(tex.rgb * scene_color.rgb, scene_color.rgb, 1 - tex.a);
    #else
        color.rgb = mix(tex.rgb * scene_color.rgb, vec3(.05), 1 - tex.a);
    #endif
        color.rgb = mix(tex.rgb, color.rgb, mask);
        color.a = 1;
    }
"""

class CustomRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "CUSTOM"
    bl_label = "Custom"
    bl_use_preview = True

    # Hides Cycles node trees in the node editor.
    bl_use_shading_nodes_custom = False

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
                    draw = BasePassRendering(datablock.data)
                    # draw.object = datablock
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
                    draw = BasePassRendering(datablock.data)
                    # draw.object = datablock
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
                    match object.data.type:
                        case "SUN":
                            # print("light: ", object.name)
                            # light_direction = mathutils.Vector((0, 0, 1))
                            # light_direction.rotate(object.matrix_world.decompose()[1])
                            # light = light_direction.to_4d()
                            # light.w = object.data.energy
                            # self.lights.append(light)
                            self.lights.append(DirectionalLightRendering(object))
                        case "POINT" | "SPOT":
                            self.lights.append(LocalLightRendering(object))


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
        fb_size = (math.floor(w * offscr_scale), math.floor(h * offscr_scale))
        final_color_format = "RGBA16"
        gbuffer_format = "RGBA16"
        normal_format = "RGBA32F"
        # if offscr_scale > 1:
        #     offscr_scale = math.floor(offscr_scale)
        basecolor = gpu.types.GPUTexture(fb_size, format=gbuffer_format)
        shadowcolor = gpu.types.GPUTexture(fb_size, format=gbuffer_format)
        normal = gpu.types.GPUTexture(fb_size, format=normal_format)
        t_lighting_mask = gpu.types.GPUTexture(fb_size, format="R8")
        z = gpu.types.GPUTexture(fb_size, format="DEPTH_COMPONENT24")
        gbuffer = gpu.types.GPUFrameBuffer(depth_slot=z, color_slots=(basecolor, shadowcolor, normal, t_lighting_mask))

        with gbuffer.bind():

            gpu.state.active_framebuffer_get().clear(color=(0, 0, 0, 0), depth=1.0)
            t_lighting_mask.clear(format="FLOAT", value=(1, 1, 1, 1))

            # Bind (fragment) shader that converts from scene linear to display space,
            # self.bind_display_space_shader(scene)

            gpu.state.depth_test_set("LESS")
            gpu.state.depth_mask_set(True)
            gpu.state.face_culling_set("BACK")

            for object in self.mesh_objects:
                draw = self.draw_calls[object.name]
                draw.draw(object.matrix_world, context.region_data, settings)
            # for key, draw in self.draw_calls.items():
            #     print(draw.object.name, " ", draw.object.hide_viewport, flush=True)
            #     draw.draw(draw.object.matrix_world, context.region_data, self.lights, settings)


            # self.unbind_display_space_shader()
        
        tscenelit = gpu.types.GPUTexture(fb_size, format=final_color_format)
        lighting = gpu.types.GPUFrameBuffer(color_slots=(tscenelit))

        with lighting.bind():
            lighting.clear(color=(0, 0, 0, 0))
            gpu.state.depth_test_set("ALWAYS")

            ps_prefix = "\n#define BACKGROUND_COLOR " + ("1" if settings.world_color_clear else "0") + "\n"
            shader = gpu.types.GPUShader(VERTEX_2D, ps_prefix + PIXEL_SCENE_LIGHTING)
            shader.bind()
            shader.uniform_float("scene_color", settings.world_color)
            shader.uniform_sampler("tbasecolor", basecolor)
            shader.uniform_sampler("tmask", t_lighting_mask)
            batch_for_shader(shader, "TRI_FAN", {"pos": ((0, 0), (1, 0), (1, 1), (0, 1))}).draw(shader)

            gpu.state.blend_set("ADDITIVE")
            for light in self.lights:
                light.draw(context.region_data, z, basecolor, shadowcolor, normal, t_lighting_mask)
            
            gpu.state.blend_set("NONE")
        
        trgbl = gpu.types.GPUTexture(fb_size, format=final_color_format)
        rgbl = gpu.types.GPUFrameBuffer(color_slots = (trgbl))

        with rgbl.bind():
            shader = gpu.types.GPUShader(VERTEX_2D, PIXEL_RGBL)
            shader.bind()
            shader.uniform_sampler("image", tscenelit)
            batch_for_shader(shader, "TRI_FAN", {"pos": ((0, 0), (1, 0), (1, 1), (0, 1))}).draw(shader)

        present_pixel_shader = PIXEL_2D

        pixel_shader_prefix = """
            vec4 finalize_color(vec4 incolor) { return incolor; }
        """
        match settings.out_buffer:
            case "SCENELIT":
                if settings.use_fxaa:
                    out_texture = trgbl
                    pixel_shader_prefix = """
                        #define FXAA_GLSL_130 1
                        #define FXAA_PC 1
                        //#define FXAA_QUALITY__PRESET 29
                    """
                    if settings.use_fxaa:
                        pixel_shader_prefix += """
                            #define USE_FXAA 1
                        """
                    present_pixel_shader = PIXEL_FXAA.replace("FXAA_HEADER", open("shaders/FXAA311.glsl").read())
                else:
                    out_texture = tscenelit
            case "BASECOLOR":
                out_texture = basecolor
            case "SHADOWCOLOR":
                out_texture = shadowcolor
            case "NORMAL":
                out_texture = normal
                pixel_shader_prefix = """
                    vec4 finalize_color(vec4 incolor) { return incolor * 0.5 + 0.5; }
                """
            case "DEPTH":
                out_texture = z
                pixel_shader_prefix = """
                    vec4 finalize_color(vec4 incolor)
                    {
                        float z = pow(incolor.x, 256);
                        return vec4(z, z, z, 1);
                    }
                """
            case "POSITION":
                present_pixel_shader = PIXEL_DEFERRED_WORLDPOS
                out_texture = tscenelit
                pixel_shader_prefix = ""

        with fb.bind():
            if settings.world_color_clear:
                fb.clear(color=settings.world_color)
            fb.clear(depth=1.0)

            gpu.state.depth_test_set("ALWAYS")
            gpu.state.depth_mask_set(True)
            
            coords = ((0, 0), (1, 0), (1, 1), (0, 1))
            shader = gpu.types.GPUShader(VERTEX_2D, pixel_shader_prefix + present_pixel_shader)
            vbo = gpu.types.GPUVertBuf(shader.format_calc(), 4)
            vbo.attr_fill("pos", coords)
            batch = gpu.types.GPUBatch(type="TRI_FAN", buf=vbo)
            shader.bind()
            shader.uniform_sampler("image", out_texture)
            shader.uniform_sampler("depth", z)
            if settings.out_buffer == "POSITION":
                region_data = context.region_data
                # shader.uniform_float("mat_view", region_data.view_matrix)
                # shader.uniform_float("mat_projection", region_data.window_matrix)
                shader.uniform_float("mat_view_projection", region_data.window_matrix @ region_data.view_matrix)
            # shader.uniform_int("view_size", (w, h))
            # shader.uniform_int("buffer_size", (rgb.width, rgb.height))
            try:
                shader.uniform_float("invScreenSize", (1.0 / w, 1.0 / h))
            except ValueError:
                pass
            batch.draw(shader)
            
class MeshDraw:
    def __init__(self, mesh):

        self.create_shaders()
        self.create_batch(mesh)

    def create_shaders(self):
        self.shader = gpu.types.GPUShader(VERTEX_SHADER, PIXEL_SHADER, geocode=GEOMETRY_SHADER)
    
    def create_batch(self, mesh):
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

        self.batch = batch_for_shader(self.shader, 'TRIS', {"position": vertices, "normal": normals, "tangent": tangents, "bitangent_sign": bitangent_signs, "uv": uvs, "color": color}, indices=indices)


    def draw_forward(self, transform, region_data, lights, settings):
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

class BasePassRendering(MeshDraw):
    def create_shaders(self):
        self.shader = gpu.types.GPUShader(
            VERTEX_SHADER,
            open("shaders/BasePassPixelShader.glsl").read(),
            geocode=GEOMETRY_SHADER)

    def draw(self, transform, region_data, settings):
        shader = self.shader
        shader.bind()

        shader.uniform_float("matrix_world", transform)
        shader.uniform_float("view_matrix", region_data.view_matrix)
        shader.uniform_float("projection_matrix", region_data.window_matrix)

        shader.uniform_bool("render_outlines", [settings.enable_outline])
        shader.uniform_float("outline_width", settings.outline_width)
        shader.uniform_float("outline_color", settings.outline_color)
        shader.uniform_float("depth_scale_exponent", settings.outline_depth_exponent)
        shader.uniform_bool("use_vertexcolor_alpha", [settings.use_vertexcolor_alpha])
        shader.uniform_bool("use_vertexcolor_rgb", [settings.use_vertexcolor_rgb])
        
        if settings.basecolor_texture:
            tbasecolor = gpu.texture.from_image(bpy.data.images[settings.basecolor_texture])
        else:
            tbasecolor = gpu.types.GPUTexture((1, 1))
            tbasecolor.clear(format="FLOAT", value=(0.5, 0.5, 0.5, 1))
        shader.uniform_sampler("tbasecolor", tbasecolor)
        
        if settings.shadowtint_texture:
            tshadowtint = gpu.texture.from_image(bpy.data.images[settings.shadowtint_texture])
        else:
            tshadowtint = gpu.types.GPUTexture((1, 1))
            tshadowtint.clear(format="FLOAT", value=(0, 0, 0, 1))
        shader.uniform_sampler("tshadowtint", tshadowtint)

        self.batch.draw(shader)

class LightRendering:
    def __init__(self, light_object):
        self.object = light_object
        # self.create_shader_info()
        self.create_shader()
    
    def get_defines(self):
        return ""
    
    # def create_shader_info(self):
    #     self.shaderinfo = gpu.types.GPUShaderCreateInfo()
    #     self.shaderinfo.vertex_source(VERTEX_2D)
    #     pixel_shader_source = open(get_path("shaders/DeferredLightPixelShader.glsl")).read()
    #     self.shaderinfo.fragment_source(pixel_shader_source)

    def create_shader(self):
        # self.shader = gpu.shader.create_from_info(self.shaderinfo)
        pixel_shader_source = open("shaders/DeferredLightPixelShader.glsl").read()
        self.shader = gpu.types.GPUShader(VERTEX_2D, pixel_shader_source, defines=self.get_defines())
        self.batch = batch_for_shader(self.shader, "TRI_FAN", {"pos": ((0, 0), (1, 0), (1, 1), (0, 1))})

    def set_uniforms(self, region_data):
        try:
            self.shader.uniform_float("energy", self.object.data.energy * self.energy_factor)
            # self.shader.uniform_float("energy", self.object.data.energy)
        except ValueError:
            # optimized out by shader compiler
            pass
        try:
            self.shader.uniform_float("mat_view_projection", region_data.window_matrix @ region_data.view_matrix)
        except ValueError:
            # this is dumb
            pass
        try:
            self.shader.uniform_float("light_color", self.object.data.color)
        except ValueError:
            pass

    def draw(self, region_data, tdepth, tbasecolor, tshadowcolor, tworldnormal, tmask):
        shader = self.shader
        shader.bind()
        shader.uniform_sampler("tdepth", tdepth)
        shader.uniform_sampler("tbasecolor", tbasecolor)
        shader.uniform_sampler("tshadowcolor", tshadowcolor)
        shader.uniform_sampler("tworldnormal", tworldnormal)
        shader.uniform_sampler("tmask", tmask)

        self.set_uniforms(region_data)

        self.batch.draw(shader)

class DirectionalLightRendering(LightRendering):
    def __init__(self, light_object):
        assert light_object.data.type == "SUN"
        super().__init__(light_object)
        self.energy_factor = 1
        light_direction = mathutils.Vector((0, 0, 1))
        light_direction.rotate(light_object.matrix_world.decompose()[1])
        self.direction = light_direction
    
    def get_defines(self):
        return super().get_defines() + """
            #define DIRECTIONAL_LIGHT 1
        """
    
    # def create_shader_info(self):
    #     super().create_shader_info()
    #     self.shaderinfo.define("DIRECTIONAL_LIGHT", "1")
    
    def set_uniforms(self, region_data):
        super().set_uniforms(region_data)
        shader = self.shader
        shader.uniform_float("light_direction", self.direction)

class LocalLightRendering(LightRendering):
    def __init__(self, light_object):
        assert light_object.data.type in ("POINT", "SPOT", "AREA")
        super().__init__(light_object)
        self.energy_factor = 0.09
        light = light_object.data

        # this cannot get instanced lights' location (eg. paticle systems, geometry nodes)
        # maybe try to fix that?
        self.location = light_object.matrix_world.to_translation()

        if light.use_custom_distance:
            self.attenuation = self.cutoff_distance
        else:
            self.attenuation = -1
    
    def get_defines(self):
        return super().get_defines() + """
            #define LOCAL_LIGHT 1
        """ + f"\n#define {self.object.data.type}_LIGHT 1\n"
    
    def set_uniforms(self, region_data):
        super().set_uniforms(region_data)
        shader = self.shader
        shader.uniform_float("light_location", self.location)

        light = self.object.data
        if light.type == "SPOT":
            light_direction = mathutils.Vector((0, 0, 1))
            light_direction.rotate(self.object.matrix_world.decompose()[1])
            shader.uniform_float("light_spot_direction", light_direction)
            shader.uniform_float("light_spot_size", light.spot_size / math.pi)
            shader.uniform_float("light_spot_blend", light.spot_blend)

class CustomRenderEngineSettings(bpy.types.PropertyGroup):
    backbuffer_scale: bpy.props.FloatProperty(name="Backbuffer Scale", default=1.0, min=0.1, max=10)
    use_fxaa: bpy.props.BoolProperty(name="FXAA", default=True)

    out_buffer: bpy.props.EnumProperty(
        items = [
            ("SCENELIT", "Deferred Lighting", ""),
            ("BASECOLOR", "Base Color", ""),
            ("SHADOWCOLOR", "Shadow Color", ""),
            ("NORMAL", "World Normal", ""),
            ("POSITION", "World Position", ""),
            ("DEPTH", "Depth", ""),
        ],
        name="Out Buffer",
        options=set()
    )

    enable_outline: bpy.props.BoolProperty(name="Render Outlines", default=True, options=set())
    outline_width: bpy.props.FloatProperty(name="Outline Width", default=1, min=0, soft_max=10, options=set())
    outline_color: bpy.props.FloatVectorProperty(name="Outline Color", size=4, default=(0, 0, 0, 1), subtype="COLOR", min=0, max=1, options=set())
    outline_depth_exponent: bpy.props.FloatProperty(name="Outline Depth Scale Exponent", default=0.75, min=0, max=1, options=set())
    shading_sharpness: bpy.props.FloatProperty(name="Shading Sharpness", default=1, subtype='FACTOR', min=0, max=1, options=set())
    fresnel_fac: bpy.props.FloatProperty(name="Fresnel Factor", default=0.5, min=0, max=1)
    use_vertexcolor_alpha: bpy.props.BoolProperty(name="Use Vertex Color Alpha", default=False, options=set(), description="Used as offset scaling")
    use_vertexcolor_rgb: bpy.props.BoolProperty(name="Use Vertex Color RGB", default=False, options=set(), description="Used as normal map for outline")

    # TODO: Materials
    basecolor_texture: bpy.props.StringProperty(name="Base Color")
    shadowtint_texture: bpy.props.StringProperty(name="Shadow Tint")

    world_color: bpy.props.FloatVectorProperty(name="World Color", size=4, default=(0.1, 0.1, 0.1, 1), subtype='COLOR', min=0, max=1, options=set())
    world_color_clear: bpy.props.BoolProperty(name="World Color Background", default=False, options=set())


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
        layout.prop(settings, "use_fxaa")
        layout.prop(settings, "out_buffer")
        layout.prop(settings, "enable_outline")
        layout.prop(settings, "outline_width")
        layout.prop(settings, "outline_color")
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
        if isinstance(light, bpy.types.Light):
            col = self.layout.column()
            col.prop(light, "color")
            col.prop(light, "energy")

            match light.type:
                case "SUN":
                    col.prop(light, "angle")
                case "POINT":
                    col.prop(light, "shadow_soft_size")
                case "SPOT":
                    col.prop(light, "shadow_soft_size")
                    col.prop(light, "spot_size")
                    col.prop(light, "spot_blend")


# RenderEngines also need to tell UI Panels that they are compatible with.
# We recommend to enable all panels marked as BLENDER_RENDER, and then
# exclude any panels that are replaced by custom panels registered by the
# render engine, or that are not supported.
def get_panels():
    exclude_panels = {
        'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes',
    }

    include_panels = {
        "DATA_PT_EEVEE_light",
        "DATA_PT_EEVEE_light_distance",
        "DATA_PT_EEVEE_shadow",
        "EEVEE_MATERIAL_PT_context_material",
        # "EEVEE_MATERIAL_PT_surface",
    }

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)
        if panel.__name__ in include_panels:
            panels.append(panel)

    return panels

classes = [
    CustomRenderEngine,
    CustomRenderEngineSettings,
    CustomRenderEnginePanel,
    # CustomRenderEngineLightPanel
]

def register():
    # Register the RenderEngine
    for c in classes:
        bpy.utils.register_class(c)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('CUSTOM')

    bpy.types.Scene.custom_render_engine = bpy.props.PointerProperty(type=CustomRenderEngineSettings)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    for panel in get_panels():
        if 'CUSTOM' in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove('CUSTOM')

