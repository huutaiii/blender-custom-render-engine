
import bpy
import nodeitems_utils

class CustomShaderNode1(bpy.types.ShaderNode):

    bl_idname = "CustomShaderNode1"
    bl_label = "Aaaaaaaaaaa"

    COMPAT_ENGINES = ["CUSTOM"]

    def init(self, context):
        self.outputs.new("NodeSocketShader", "aaaaaa")
        self.inputs.new("NodeSocketColor", "basecolor")
        self.inputs["basecolor"].default_value = (1, 1, 1, 1)
    
class CustomShaderNodeCategory(nodeitems_utils.NodeCategory):
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'NODE_EDITOR' and
            context.space_data.tree_type == 'ShaderNodeTree')

def shader_node_poll(context):
    return context.engine == "CUSTOM"

def register():
    bpy.utils.register_class(CustomShaderNode1)
    nodeitems_utils.register_node_categories(
        "CUSTOMSHADER",
        [CustomShaderNodeCategory("SH_NEW_CUSTOMSHADER", "CustomShaders", items=[
            nodeitems_utils.NodeItem("CustomShaderNode1", poll=shader_node_poll)
        ])]
    )

def unregister():
    nodeitems_utils.unregister_node_categories("CUSTOMSHADER")
    bpy.utils.unregister_class(CustomShaderNode1)