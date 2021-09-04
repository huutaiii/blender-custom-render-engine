
New-Item -ItemType Directory .\custom_render_engine -Force >$null
New-Item -ItemType Directory .\custom_render_engine\shaders -Force >$null

Copy-Item -Path .\src\custom_render_engine.py -Destination .\custom_render_engine\__init__.py -Force
Copy-Item -Path .\src\operators.py -Destination .\custom_render_engine\operators.py -Force
foreach ($file in ("VertexShader.glsl", "GeometryShader.glsl", "PixelShader.glsl"))
{
    Copy-Item -Path .\src\shaders\$file -Destination .\custom_render_engine\shaders\$file
}

Compress-Archive -Path .\custom_render_engine -DestinationPath .\custom_render_engine.zip -Force
