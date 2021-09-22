
import bpy
import numpy as np
import mathutils
import bl_math

# Maps calculated normals into vertex color when using custom split normals
def bake_vertex_normals(object, write_z, merge_axis, merge_threshold):
    mesh = object.data
    mesh.calc_tangents()
    normals = np.empty((len(mesh.loops), 3), dtype=np.float32)
    mesh.loops.foreach_get("normal", np.reshape(normals, len(mesh.loops) * 3))
    tangents = np.empty((len(mesh.loops), 3), dtype=np.float32)
    mesh.loops.foreach_get("tangent", np.reshape(tangents, len(mesh.loops) * 3))
    bitangents = np.empty((len(mesh.loops), 3), dtype=np.float32)
    mesh.loops.foreach_get("bitangent", np.reshape(bitangents, len(mesh.loops) * 3))
    bitangents = np.negative(bitangents)
    
    vertex_normals = np.copy(normals)
    for i in range(len(mesh.loops)):
        vertex_index = mesh.loops[i].vertex_index
        normal = mathutils.Vector(mesh.vertices[vertex_index].normal)
        if merge_axis == "X":
            if abs(mesh.vertices[vertex_index].co.x) < merge_threshold:
                normal.x = 0
        if merge_axis == "Y":
            if abs(mesh.vertices[vertex_index].co.y) < merge_threshold:
                normal.y = 0
        if merge_axis == "Z":
            if abs(mesh.vertices[vertex_index].co.z) < merge_threshold:
                normal.z = 0
        normal.normalize()
        vertex_normals[i] = normal
    
    vertex_colors = mesh.vertex_colors.active.data
    for i in range(len(vertex_colors)):
        
        tangent_space = mathutils.Matrix((tangents[i], bitangents[i], normals[i]))
        
        vertex_normal = mathutils.Vector(vertex_normals[i])
        normal = vertex_normal @ tangent_space.inverted()
        normal = normal / 2 + mathutils.Vector((0.5, 0.5, 0.5))
        
        if write_z:
            vertex_colors[i].color = (normal.x, normal.y, normal.z, vertex_colors[i].color[3])
        else:
            vertex_colors[i].color = (normal.x, normal.y, vertex_colors[i].color[2], vertex_colors[i].color[3])

class OBJECT_OT_bake_vertex_normals(bpy.types.Operator):
    bl_idname = "object.bake_vertex_normals"
    bl_label = "Bake Vertex Normals"
    # bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    write_z_component: bpy.props.BoolProperty(name="Write Z Component")
    merge_axis: bpy.props.EnumProperty(name = "Merge Axis",
        items = [
            ("NONE", "None", "", 0),
            ("X", "X", "", 1),
            ("Y", "Y", "", 2),
            ("Z", "Z", "", 3)
        ])
    merge_threshold: bpy.props.FloatProperty(name="Merge Threshold", default=0.001, subtype='DISTANCE', min=0)

    @classmethod
    def poll(self, context):
        if len(context.selected_objects) == 0:
            return False
        for object in context.selected_objects:
            # if not (object.type == "MESH" and (object.data.has_custom_normals or object.data.use_auto_smooth)):
            if object.type != "MESH":
                return False
        return True

    def execute(self, context):
        for object in context.selected_objects:
            bake_vertex_normals(object, self.write_z_component, self.merge_axis, self.merge_threshold)
        return {"FINISHED"}

def draw_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("object.bake_vertex_normals", text="Bake Vertex Normals")

def register():
    bpy.utils.register_class(OBJECT_OT_bake_vertex_normals)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_menu)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_bake_vertex_normals)
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_menu)
