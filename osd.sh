#!/bin/sh

rm previews/* font/*.h

python3 osd.py --width 8 --height 16 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 1 --auto_font_size 1
python3 osd.py --width 16 --height 32 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 2 --auto_font_size 1
python3 osd.py --width 24 --height 48 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 2 --auto_font_size 1
python3 osd.py --width 48 --height 96 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 5 --auto_font_size 1

mkdir -p font
mv *.h font/