from PIL import Image, ImageDraw, ImageFont
import numpy as np
import argparse

def render_char_with_outline_i4_preserve_aspect(char, font_path, out_size, font_scale=1.3, outline_width=2):
    w, h = out_size
    font_size = int(min(w, h) * font_scale)
    font = ImageFont.truetype(font_path, font_size)

    # 创建大画布（避免字符边缘被裁剪）
    canvas_size = (w * 4, h * 4)
    img = Image.new("L", canvas_size, 0)
    draw = ImageDraw.Draw(img)

    # 获取字符边界
    bbox = draw.textbbox((0, 0), char, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_x, text_y = bbox[0], bbox[1]

    # 居中位置（根据 bbox 偏移修正）
    center_x = (canvas_size[0] - text_w) // 2 - text_x
    center_y = (canvas_size[1] - text_h) // 2 - text_y

    # 描边（灰色）
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.text((center_x + dx, center_y + dy), char, font=font, fill=0x88)

    # 主体（白色）
    draw.text((center_x, center_y), char, font=font, fill=0xFF)

    # 剪裁字符区域
    cropped = img.crop(img.getbbox())

    # 保持比例缩放，并居中粘贴到目标尺寸图像
    char_w, char_h = cropped.size
    scale = min(w / char_w, h / char_h)
    new_size = (int(char_w * scale), int(char_h * scale))
    resized = cropped.resize(new_size, Image.NEAREST)

    final_img = Image.new("L", (w, h), 0)
    offset = ((w - new_size[0]) // 2, (h - new_size[1]) // 2)
    final_img.paste(resized, offset)

    # 转为 numpy 并量化为 I4（0x0, 0x8, 0xF）
    arr = np.array(final_img)

    def quantize(val):
        if val >= 200:
            return 0xF
        elif val >= 80:
            return 0x8
        else:
            return 0x0

    flat = arr.flatten()
    quantized = np.array([quantize(p) for p in flat], dtype=np.uint8)

    if len(quantized) % 2 != 0:
        quantized = np.append(quantized, 0)

    packed = [(quantized[i] << 4) | quantized[i + 1] for i in range(0, len(quantized), 2)]
    return packed



def render_char_with_outline_i4(char, font_path, out_size, font_scale=1.3, outline_width=2):
    w, h = out_size
    font_size = int(min(w, h) * font_scale)
    font = ImageFont.truetype(font_path, font_size)

    # 设定一个稍大的 canvas 来容纳字体并添加描边
    canvas_size = (w * 2, h * 2)  # 增大背景大小，避免字体边缘被裁剪
    img = Image.new("L", canvas_size, 0)  # 使用单通道灰度图
    draw = ImageDraw.Draw(img)

    # 获取文本尺寸
    bbox = draw.textbbox((0, 0), char, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (canvas_size[0] - text_w) // 2
    y = (canvas_size[1] - text_h) // 2

    # 描边（灰色，值 0x8）
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.text((x + dx, y + dy), char, font=font, fill=8 * 17)  # 灰色填充

    # 主体（白色）
    draw.text((x, y), char, font=font, fill=15 * 17)  # 白色填充

    # 裁剪非零区域
    bbox = img.getbbox()
    cropped = img.crop(bbox)

    # 缩放到目标大小
    resized = cropped.resize((w, h), Image.Resampling.LANCZOS)
    gray = np.array(resized)

    def quantize(val):
        if val >= 200:
            return 0xF
        elif val >= 80:
            return 0x8
        else:
            return 0x0

    flat = gray.flatten()
    quantized = np.array([quantize(p) for p in flat], dtype=np.uint8)

    if len(quantized) % 2 != 0:
        quantized = np.append(quantized, 0)

    packed = [(quantized[i] << 4) | quantized[i + 1] for i in range(0, len(quantized), 2)]
    return packed

def safe_char_name(c):
    return c if c.isalnum() else f"u{ord(c):04X}"

def export_chars_white_gray_i4_header(chars, font_path, out_size, outline_width=2):
    w, h = out_size
    header_filename = f"font_chars_i4_{w}x{h}.h"
    lines = [
        f"#ifndef FONT_I4_WHITE_GRAY_{w}x{h}_H",
        f"#define FONT_I4_WHITE_GRAY_{w}x{h}_H",
        "",
        f"#include <stdint.h>",
        "",
        f"// I4 Font: white(0xF), gray(0x8), transparent(0x0). Size {w}x{h}, 2 pixels per byte.",
        ""
    ]

    array_entries = []

    for c in chars:
        arr = render_char_with_outline_i4_preserve_aspect(c, font_path, out_size, outline_width=outline_width)
        name = f"char_{safe_char_name(c)}_{w}x{h}_i4"
        array_entries.append(f"    {{ .width = {w}, .height = {h}, .pdata = {name} }},")

        lines.append(f"static const uint8_t {name}[{len(arr)}] = {{")
        for i in range(0, len(arr), w // 2):
            line = ", ".join(f"0x{val:02X}" for val in arr[i:i + w // 2])
            lines.append("    " + line + ",")
        lines.append("};\n")

    # 添加 bitmap_i4_t 数组
    lines.append(f"static const bitmap_i4_t i4_{w}x{h}[{len(chars)}] = {{")
    lines.extend(array_entries)
    lines.append("};")
    lines.append("")
    lines.append(f"#endif // FONT_I4_WHITE_GRAY_{w}x{h}_H")

    with open(header_filename, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ I4 header saved: {header_filename}")


# 示例调用
if __name__ == "__main__":
    # 使用 argparse 处理命令行参数
    parser = argparse.ArgumentParser(description="Generate I4 font header")
    parser.add_argument(
        '--width', type=int, required=True, help='Width of the output font image (e.g., 48)'
    )
    parser.add_argument(
        '--height', type=int, required=True, help='Height of the output font image (e.g., 64)'
    )
    parser.add_argument(
        '--font', type=str, required=True, help='Path to the font file (e.g., Roboto-Light.ttf)'
    )

    args = parser.parse_args()
    out_size = (args.width, args.height)
    font_path = args.font
    export_chars_white_gray_i4_header(
        chars="0123456789- :",
        font_path=font_path,  # 替换为你自己的字体
        out_size=out_size,
        outline_width=2
    )
