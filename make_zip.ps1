
New-Item -ItemType Directory .\custom_render_engine -Force

Copy-Item -Path .\custom_render_engine.py -Destination .\custom_render_engine\__init__.py -Force
foreach ($file in ("VertexShader.glsl", "GeometryShader.glsl", "PixelShader.glsl"))
{
    Copy-Item -Path $file -Destination .\custom_render_engine\$file
}

Compress-Archive -Path .\custom_render_engine -DestinationPath .\custom_render_engine.zip -Force
