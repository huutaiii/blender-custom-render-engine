
bl_info = {
    "name": "Custom Render Engine",
    # "description": "Single line explaining what this script exactly does.",
    "author": "huutai",
    "version": (0, 1),
    "blender": (3, 3, 0),
    "category": "Render",
}

import os, sys

if os.name == 'nt':
    delimiter = '\\'
if os.name == 'posix':
    delimiter = '/'
if not delimiter:
    raise RuntimeError("Platform not supported")
names = __file__.split(delimiter)
path = delimiter.join(names[:len(names)-1])

sys.path.append(path)
os.chdir(path)

from modules import custom_render_engine, operators, material

def register():
    custom_render_engine.register()
    operators.register()
    material.register()

def unregister():
    custom_render_engine.unregister()
    operators.unregister()
    material.unregister()

if __name__ == "__main__":
    register()