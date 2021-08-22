
$BLENDER="C:\\Program Files\\Blender Foundation\\Blender 2.93\\blender.exe"
$FILE=".\test_file.blend"

# Stop-Process -Name blender
& $BLENDER $FILE --python custom_render_engine.py --window-geometry 0 0 900 1000
