#! /bin/bash

which zip >/dev/null || { echo Please install zip; exit 1; }

SOURCE=src
TARGET=custom_render_engine

echo Installing files
find $SOURCE -type f | while read file
do
    echo $file
    install -D $file ${file/$SOURCE/$TARGET}
done
mv $TARGET/custom_render_engine.py $TARGET/__init__.py

echo Creating zip
zip $TARGET.zip -r $TARGET

echo Done
