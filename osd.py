#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化版 OSD 变量字体生成工具
- 小尺寸（如8x16）自动采用窄细参数，避免变形/描边丢失
- 量化灰度更细腻，描边更清晰
- 建议配合 Variable Font（如 RobotoFlex-VariableFont.ttf）
"""
from scipy.ndimage import binary_dilation
from PIL import Image, ImageDraw
import numpy as np
import freetype
import argparse
import os

def get_small_size_var_coords(w, h):
    # 针对小尺寸，优先选用最细最窄
    if w <= 10 or h <= 20:
        return [70, 300]
    elif w <= 16 or h <= 32:
        return [85, 400]
    return None

def find_best_var_coords(font_path, canvas_size, outline_width, font_pixel_size, test_char='0',
                         wdth_range=(50, 150), wght_range=(200, 900), wdth_step=5, wght_step=50):
    face = freetype.Face(font_path)
    results = []
    for wdth in range(wdth_range[0], wdth_range[1]+1, wdth_step):
        for wght in range(wght_range[0], wght_range[1]+1, wght_step):
            try:
                face.set_var_design_coords([float(wdth), float(wght)])
                face.set_pixel_sizes(0, font_pixel_size)
                face.load_char(test_char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
                glyph = face.glyph
                width = glyph.bitmap.width + 2 * outline_width
                height = glyph.bitmap.rows + 2 * outline_width
                if width <= canvas_size[0] and height <= canvas_size[1]:
                    results.append(([float(wdth), float(wght)], width*height))
            except Exception:
                continue
    if results:
        # 面积最大优先
        return sorted(results, key=lambda x: -x[1])[0][0]
    return None


def quantize(val):
    # 更细致的灰度分级
    if val >= 220:
        return 0xF
    elif val >= 160:
        return 0x8
    elif val >= 80:
        return 0x7
    else:
        return 0x0

def safe_char_name(c):
    if c.isalnum():
        return c
    return "u{:04X}".format(ord(c))

def find_max_font_size(font_path, canvas_size, outline_width, var_coords=None, min_size=5, max_size=256, test_char='0'):
    face = freetype.Face(font_path)
    def check_font_size_fit(font_pixel_size):
        try:
            if var_coords is not None:
                face.set_var_design_coords(var_coords)
            face.set_pixel_sizes(0, font_pixel_size)
            face.load_char(test_char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            glyph = face.glyph
            width = glyph.bitmap.width + 2 * outline_width
            height = glyph.bitmap.rows + 2 * outline_width
            return width <= canvas_size[0] and height <= canvas_size[1]
        except Exception:
            return False
    low = min_size
    high = max_size
    best = min_size
    while low <= high:
        mid = (low + high) // 2
        if check_font_size_fit(mid):
            best = mid
            low = mid + 1
        else:
            high = mid - 1
    return best

def simple_dilate_no_wrap(mask, width):
    """对 mask 进行 dilation，不 wrap，不使用卷积核边缘重复"""
    structure = np.ones((width * 2 + 1, width * 2 + 1), dtype=bool)
    return binary_dilation(mask, structure=structure)

def render_char_precise_position_with_clean_outline(
    char,
    font_path,
    out_size,
    font_pixel_size=None,
    outline_width=1,
    var_coords=None
):
    w, h = out_size
    canvas = np.zeros((h, w), dtype=np.uint8)

    face = freetype.Face(font_path)
    if var_coords is not None:
        try:
            face.set_var_design_coords(var_coords)
        except Exception as e:
            print(f"⚠️ 设置变量字体轴值失败: {e}")

    face.set_pixel_sizes(0, font_pixel_size)
    face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    glyph = face.glyph
    bitmap = glyph.bitmap

    bitmap_w, bitmap_h = bitmap.width, bitmap.rows
    bitmap_left = glyph.bitmap_left
    bitmap_top = glyph.bitmap_top

    arr = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap_h, bitmap_w)

    # 字形 advance.x 单位为 1/64 像素，转换为像素单位
    advance_px = glyph.advance.x / 64

    # 水平居中处理
    if char in ('-', ':'):
        # 针对窄符号，直接按位图宽度居中
        offset_x = int(round((w - bitmap_w) / 2))
    else:
        # 以字形 advance 宽度为设计宽度居中，bitmap_left 是位图左边距，需加上
        canvas_center_x = w / 2
        glyph_center_x = advance_px / 2
        offset_x = int(round(canvas_center_x - glyph_center_x)) + bitmap_left

    # 限制偏移范围，避免越界
    offset_x = max(0, min(offset_x, w - bitmap_w))

    # 垂直居中，基于 bitmap_top 和 bitmap 高度定位字符垂直中心于画布中心
    if char in ('-', ':'):
        canvas_center_y = h / 2
        offset_y = int(round(canvas_center_y - bitmap_h / 2))
    else:
        glyph_center_y = bitmap_top - bitmap_h / 2
        canvas_center_y = h / 2
        offset_y = int(round(canvas_center_y - glyph_center_y))
        offset_y = max(0, min(offset_y, h - bitmap_h))

    # 将字形灰度拷贝到画布
    canvas[offset_y:offset_y + bitmap_h, offset_x:offset_x + bitmap_w] = arr

    # 生成 mask 与描边
    mask = canvas > 10
    if outline_width > 0:
        dilated = simple_dilate_no_wrap(mask, outline_width)
    else:
        dilated = mask.copy()
    outline_mask = np.logical_and(dilated, np.logical_not(mask))

    result = np.zeros_like(canvas, dtype=np.uint8)
    result[outline_mask] = 136  # 灰色描边
    result[mask] = 255          # 白色字体

    # 量化为 4-bit (I4)
    def quantize(val):
        return 0xF if val >= 200 else 0x8 if val >= 100 else 0x0

    flat = result.flatten()
    quantized = np.array([quantize(p) for p in flat], dtype=np.uint8)
    if len(quantized) % 2 != 0:
        quantized = np.append(quantized, 0)

    packed = [(quantized[i] << 4) | quantized[i + 1] for i in range(0, len(quantized), 2)]
    return packed

def export_chars_black_white_gray_i4_header(chars, font_path, out_size, outline_width=1, font_pixel_size=None, var_coords=None):
    w, h = out_size

    if font_pixel_size is None:
        print("🔍 Searching max font pixel size to fit canvas and outline...")
        font_pixel_size = find_max_font_size(font_path, out_size, outline_width, var_coords=var_coords)
        print(f"✅ Max font_pixel_size found: {font_pixel_size}")

    var_suffix = ""

    header_filename = f"font_chars_i4_{w}x{h}{var_suffix}.h"
    lines = [
        f"#ifndef FONT_I4_BLACK_WHITE_GRAY_{w}x{h}{var_suffix}_H",
        f"#define FONT_I4_BLACK_WHITE_GRAY_{w}x{h}{var_suffix}_H",
        "",
        "#include <stdint.h>",
        "",
        f"// I4 Font: white(0xF), gray(0xA/0x6), black/transparent(0x0). Size {w}x{h}, 2 pixels per byte.",
        f"// font_pixel_size={font_pixel_size}, outline_width={outline_width}, var_coords={var_coords}",
        "",
    ]
    array_entries = []
    for c in chars:
        arr = render_char_precise_position_with_clean_outline(c, font_path, out_size, font_pixel_size=font_pixel_size, outline_width=outline_width, var_coords=var_coords)
        name = f"char_{safe_char_name(c)}_{w}x{h}_i4{var_suffix}"
        array_entries.append(f"    {{ .width = {w}, .height = {h}, .pdata = {name} }},")
        lines.append(f"static const uint8_t {name}[{len(arr)}] = {{")
        for i in range(0, len(arr), w // 2):
            line = ", ".join(f"0x{val:02X}" for val in arr[i : i + w // 2])
            lines.append("    " + line + ",")
        lines.append("};\n")
    lines.append(f"static const bitmap_i4_t i4_{w}x{h}{var_suffix}[{len(chars)}] = {{")
    lines.extend(array_entries)
    lines.append("};")
    lines.append("")
    lines.append(f"#endif // FONT_I4_BLACK_WHITE_GRAY_{w}x{h}{var_suffix}_H")
    with open(header_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ I4 header saved: {header_filename}")

def generate_preview_image(chars, font_path, out_size, outline_width, font_pixel_size, save_path, var_coords=None):
    w, h = out_size
    margin = 4
    cols = 16
    rows = (len(chars) + cols - 1) // cols
    preview_w = cols * (w + margin) + margin
    preview_h = rows * (h + margin) + margin

    img = Image.new("RGBA", (preview_w, preview_h), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)

    for idx, c in enumerate(chars):
        packed = render_char_precise_position_with_clean_outline(
            c, font_path, out_size, font_pixel_size=font_pixel_size, outline_width=outline_width, var_coords=var_coords
        )

        pixels = np.zeros(h * w, dtype=np.uint8)
        for i, val in enumerate(packed):
            high = (val >> 4) & 0xF
            low = val & 0xF
            pixels[i * 2] = high * 17
            if i * 2 + 1 < pixels.size:
                pixels[i * 2 + 1] = low * 17
        pixels = pixels.reshape((h, w))

        char_img = Image.fromarray(pixels, mode='L').convert("RGBA")
        datas = char_img.getdata()
        newData = []
        for item in datas:
            if item[0] >= 220:
                newData.append((255, 255, 255, 255))
            elif item[0] >= 150:
                newData.append((255, 0, 0, 255))
            elif item[0] >= 80:
                newData.append((200, 200, 200, 255))
            else:
                newData.append((0, 0, 0, 0))
        char_img.putdata(newData)

        x = margin + (idx % cols) * (w + margin)
        y = margin + (idx // cols) * (h + margin)
        img.paste(char_img, (x, y), char_img)

        draw.text((x, y + h - 12), c if c.isprintable() else f"U+{ord(c):04X}", fill=(200,200,200,255))

    img.save(save_path)
    print(f"✅ 字符预览图保存至: {save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Variable Font（OTF/TTF）支持的OSD字体生成器，自动计算最佳var_coords")
    parser.add_argument("--width", type=int, required=True, help="字体位图宽度")
    parser.add_argument("--height", type=int, required=True, help="字体位图高度")
    parser.add_argument("--font", type=str, required=True, help="OTF或TTF字体文件路径（可变字体）")
    parser.add_argument("--chars", type=str, default="0123456789- :", help="需要生成的字符")
    parser.add_argument("--outline_width", type=int, default=1, help="描边宽度（像素）")
    parser.add_argument("--auto_font_size", type=int, default=1, choices=[0,1], help="自动计算最大字体像素大小")
    parser.add_argument("--sizes", type=int, nargs="*", default=[], help="批量测试字体像素大小，覆盖auto_font_size")
    parser.add_argument("--preview_dir", type=str, default="previews", help="预览图保存目录")
    args = parser.parse_args()

    if not (args.font.lower().endswith('.ttf') or args.font.lower().endswith('.otf')):
        print("Error: 仅支持 .ttf 和 .otf 字体文件！")
        exit(1)

    os.makedirs(args.preview_dir, exist_ok=True)

    if args.sizes:
        for size in args.sizes:
            print(f"===> 处理字体像素大小: {size}")
            out_size = (args.width, args.height)
            var_coords = get_small_size_var_coords(args.width, args.height)
            if var_coords is None:
                var_coords = find_best_var_coords(args.font, out_size, args.outline_width, size)
            print(f"变量字体轴参数: {var_coords}")
            suffix = ""
            if var_coords:
                suffix = f"_wdth{int(var_coords[0])}_wght{int(var_coords[1])}"
            preview_path = os.path.join(args.preview_dir, f"preview_{args.width}x{args.height}_size{size}{suffix}.png")
            generate_preview_image(
                args.chars,
                args.font,
                out_size,
                args.outline_width,
                font_pixel_size=size,
                save_path=preview_path,
                var_coords=var_coords
            )
    else:
        font_pixel_size = None
        if args.auto_font_size:
            print("🔍 自动查找最大字体像素大小...")
            # 优先用小尺寸参数
            var_coords = get_small_size_var_coords(args.width, args.height)
            if var_coords is not None:
                font_pixel_size = find_max_font_size(args.font, (args.width, args.height), args.outline_width, var_coords=var_coords)
            else:
                font_pixel_size = find_max_font_size(args.font, (args.width, args.height), args.outline_width)
        else:
            font_pixel_size = args.height

        # 优先用小尺寸参数
        if 'var_coords' not in locals() or var_coords is None:
            var_coords = get_small_size_var_coords(args.width, args.height)
        if var_coords is None:
            var_coords = find_best_var_coords(args.font, (args.width, args.height), args.outline_width, font_pixel_size)
        print(f"变量字体轴参数: {var_coords}")

        export_chars_black_white_gray_i4_header(
            args.chars,
            args.font,
            (args.width, args.height),
            outline_width=args.outline_width,
            font_pixel_size=font_pixel_size,
            var_coords=var_coords
        )
        suffix = ""
        if var_coords:
            suffix = f"_wdth{int(var_coords[0])}_wght{int(var_coords[1])}"
        preview_path = os.path.join(args.preview_dir, f"preview_{args.width}x{args.height}_size{font_pixel_size}{suffix}.png")
        generate_preview_image(
            args.chars,
            args.font,
            (args.width, args.height),
            args.outline_width,
            font_pixel_size=font_pixel_size,
            save_path=preview_path,
            var_coords=var_coords
        )