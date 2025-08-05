#!/bin/sh

rm previews/* font/*.h

./ft2bitmap_gen ../fonts/Roboto-Light.ttf 8 16 1 "0123456789- :"
./ft2bitmap_gen ../fonts/Roboto-Medium.ttf 16 32 2 "0123456789- :"
./ft2bitmap_gen ../fonts/Roboto-Medium.ttf 24 48 2 "0123456789- :"
./ft2bitmap_gen ../fonts/Roboto-Medium.ttf 48 96 4 "0123456789- :"

mkdir -p font
mv *.h font/