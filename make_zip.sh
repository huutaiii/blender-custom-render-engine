#! /bin/bash

which zip >/dev/null || { echo Please install zip; exit 1; }

SOURCE=src
TARGET=custom_render_engine

rm $TARGET -r
rm $TARGET.zip

echo Installing files
find $SOURCE -type f -name '*.py' -o -name '*.glsl' | while read file
do
    echo $file
    install -D $file ${file/$SOURCE/$TARGET}
done
mv $TARGET/custom_render_engine.py $TARGET/__init__.py

echo Creating zip
zip $TARGET.zip -r $TARGET

echo Done
