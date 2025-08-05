#!/bin/sh

rm previews/* font/*.h

python3 osd.py --width 8 --height 16 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 1 --auto_font_size 1
python3 osd.py --width 16 --height 32 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 2 --auto_font_size 1
python3 osd.py --width 24 --height 48 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 2 --auto_font_size 1
python3 osd.py --width 48 --height 96 --font ./fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf --chars "0123456789- :" --outline_width 4 --auto_font_size 1

#./ft2bitmap_gen fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf 8 16 1 "0123456789- :"
#./ft2bitmap_gen fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf 16 32 2 "0123456789- :"
#./ft2bitmap_gen fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf 24 48 2 "0123456789- :"
#./ft2bitmap_gen fonts/RobotoFlex-VariableFont_GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght.ttf 48 96 3 "0123456789- :"

mkdir -p font
mv *.h font/