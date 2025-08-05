#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_STROKER_H

// 配置参数
#define BASE_OUTLINE_RATIO 0.04f
#define MIN_OUTLINE_WIDTH 0.5f
#define MAX_OUTLINE_WIDTH 3.0f
#define OUTLINE_COLOR 0x00

typedef struct {
    int width;
    int height;
    int advance;
    int bearingX;
    int bearingY;
} GlyphMetrics;

typedef struct {
    int width;
    int height;
    const uint8_t *data;
} bitmap_i4_t;

// 优化后的双线性缩放函数
void scale_bitmap(const unsigned char* src, int src_w, int src_h,
                  unsigned char* dst, int dst_w, int dst_h) {
    if (src_w == dst_w && src_h == dst_h) {
        memcpy(dst, src, src_w * src_h);
        return;
    }

    float x_ratio = (float)src_w / dst_w;
    float y_ratio = (float)src_h / dst_h;

    for (int y = 0; y < dst_h; y++) {
        for (int x = 0; x < dst_w; x++) {
            float src_x = x * x_ratio;
            float src_y = y * y_ratio;

            int x1 = (int)src_x;
            int y1 = (int)src_y;
            int x2 = (x1 < src_w - 1) ? x1 + 1 : x1;
            int y2 = (y1 < src_h - 1) ? y1 + 1 : y1;

            float dx = src_x - x1;
            float dy = src_y - y1;

            // 边界检查
            if (x1 >= src_w) x1 = src_w - 1;
            if (y1 >= src_h) y1 = src_h - 1;
            if (x2 >= src_w) x2 = src_w - 1;
            if (y2 >= src_h) y2 = src_h - 1;

            // 双线性插值
            float a = src[y1 * src_w + x1] * (1 - dx) * (1 - dy);
            float b = src[y1 * src_w + x2] * dx * (1 - dy);
            float c = src[y2 * src_w + x1] * (1 - dx) * dy;
            float d = src[y2 * src_w + x2] * dx * dy;

            dst[y * dst_w + x] = (unsigned char)(a + b + c + d);
        }
    }
}

// I4格式转换函数（4bpp，每字节存两个像素）
void convert_to_i4(const unsigned char* src, unsigned char* dst, int width, int height) {
    int padded_width = (width + 1) & ~1; // 宽度偶数化

    for (int y = 0; y < height; y++) {
        for (int x = 0; x < padded_width; x += 2) {
            int src_idx1 = y * width + x;
            int src_idx2 = (x + 1 < width) ? (y * width + x + 1) : src_idx1;

            unsigned char pix1 = (x < width) ? src[src_idx1] : 0;
            unsigned char pix2 = (x + 1 < width) ? src[src_idx2] : 0;

            // 优化灰度映射：更平滑的过渡
            unsigned char p1;
            if (pix1 < 64)
                p1 = 0x0;
            else if (pix1 < 192)
                p1 = 0x8;
            else
                p1 = 0xF;

            unsigned char p2;
            if (pix2 < 64)
                p2 = 0x0;
            else if (pix2 < 192)
                p2 = 0x8;
            else
                p2 = 0xF;

            dst[y * (padded_width / 2) + x / 2] = (p1 << 4) | p2;
        }
    }
}

/**
 * @brief 自动计算合适的 pixel_size
 */
int auto_calc_pixel_size(FT_Face face, int target_height) {
    int pixel_size = target_height;
    int last_valid = 1;

    for (; pixel_size > 0; pixel_size--) {
        FT_Set_Pixel_Sizes(face, 0, pixel_size);
        FT_Load_Char(face, 'M', FT_LOAD_DEFAULT);

        int ascender = face->size->metrics.ascender >> 6;
        int descender = abs(face->size->metrics.descender >> 6);
        int height = ascender + descender;

        if (height <= target_height) {
            last_valid = pixel_size;
            if (height >= target_height * 0.95) {
                break;
            }
        }
    }

    if (pixel_size <= 0) pixel_size = last_valid;
    if (pixel_size <= 0) pixel_size = 1;

    printf("Auto-calculated pixel_size: %d for target height %d\n",
           pixel_size, target_height);

    return pixel_size;
}

// 计算自适应描边宽度
float calculate_outline_width(int pixel_size, int target_height) {
    // 小尺寸字体使用更细的描边
    if (target_height <= 16) {
        return 0.5f;
    }

    float outline_width = pixel_size * BASE_OUTLINE_RATIO;
    if (outline_width < MIN_OUTLINE_WIDTH)
        outline_width = MIN_OUTLINE_WIDTH;
    else if (outline_width > MAX_OUTLINE_WIDTH)
        outline_width = MAX_OUTLINE_WIDTH;
    return outline_width;
}

// 优化后的字符渲染函数
void render_char_with_outline(FT_Face face, int charcode,
                             unsigned char** buffer,
                             GlyphMetrics* metrics,
                             float outline_width) {
    FT_Error error;

    // 加载字符轮廓
    if ((error = FT_Load_Char(face, charcode, FT_LOAD_NO_BITMAP))) {
        fprintf(stderr, "Failed to load char %c: %d\n", charcode, error);
        *buffer = NULL;
        return;
    }

    // 创建描边器
    FT_Stroker stroker;
    FT_Stroker_New(face->glyph->library, &stroker);
    FT_Stroker_Set(stroker,
                   (FT_Fixed)(outline_width * 64),
                   FT_STROKER_LINECAP_ROUND,
                   FT_STROKER_LINEJOIN_ROUND,
                   0);

    // 创建描边字形
    FT_Glyph outline_glyph;
    FT_Get_Glyph(face->glyph, &outline_glyph);
    FT_Glyph_StrokeBorder(&outline_glyph, stroker, 0, 1);
    FT_Glyph_To_Bitmap(&outline_glyph, FT_RENDER_MODE_NORMAL, 0, 1);
    FT_BitmapGlyph outline_bitmap_glyph = (FT_BitmapGlyph)outline_glyph;
    FT_Bitmap* outline_bitmap = &outline_bitmap_glyph->bitmap;

    // 渲染主体字形
    if ((error = FT_Load_Char(face, charcode, FT_LOAD_RENDER))) {
        fprintf(stderr, "Failed to load char %c bitmap: %d\n", charcode, error);
        FT_Stroker_Done(stroker);
        FT_Done_Glyph(outline_glyph);
        *buffer = NULL;
        return;
    }
    FT_Bitmap* body_bitmap = &face->glyph->bitmap;

    // 计算最终位图尺寸
    int final_width = outline_bitmap->width;
    int final_height = outline_bitmap->rows;

    // 特殊处理小尺寸字符
    if (face->size->metrics.height >> 6 <= 16) {
        final_width = body_bitmap->width;
        final_height = body_bitmap->rows;
    }

    *buffer = (unsigned char*)calloc(final_width * final_height, 1);
    if (!*buffer) {
        fprintf(stderr, "Memory alloc failed for char %c\n", charcode);
        FT_Stroker_Done(stroker);
        FT_Done_Glyph(outline_glyph);
        return;
    }

    // 设置度量信息
    metrics->width = final_width;
    metrics->height = final_height;
    metrics->bearingX = face->glyph->bitmap_left;
    metrics->bearingY = face->glyph->bitmap_top;
    metrics->advance = face->glyph->advance.x >> 6;

    // 小尺寸字体不添加描边
    if (face->size->metrics.height >> 6 <= 16) {
        // 直接复制主体位图
        for (int y = 0; y < final_height; y++) {
            for (int x = 0; x < final_width; x++) {
                (*buffer)[y * final_width + x] =
                    body_bitmap->buffer[y * body_bitmap->pitch + x];
            }
        }
    } else {
        // 计算偏移量
        int offset_x = face->glyph->bitmap_left - outline_bitmap_glyph->left;
        int offset_y = outline_bitmap_glyph->top - face->glyph->bitmap_top;

        // 合并描边和主体
        for (int y = 0; y < final_height; y++) {
            for (int x = 0; x < final_width; x++) {
                unsigned char outline_val = outline_bitmap->buffer[y * outline_bitmap->pitch + x];
                unsigned char body_val = 0;

                int bx = x + offset_x;
                int by = y + offset_y;

                if (bx >= 0 && bx < body_bitmap->width &&
                    by >= 0 && by < body_bitmap->rows) {
                    body_val = body_bitmap->buffer[by * body_bitmap->pitch + bx];
                }

                // 优化混合：描边优先，主体覆盖
                unsigned char final_val;
                if (body_val > 160) {
                    final_val = 255; // 主体核心区域
                } else if (body_val > 0) {
                    final_val = 192; // 主体边缘
                } else if (outline_val > 0) {
                    final_val = 64; // 描边区域
                } else {
                    final_val = 0; // 背景
                }

                (*buffer)[y * final_width + x] = final_val;
            }
        }
    }

    FT_Stroker_Done(stroker);
    FT_Done_Glyph(outline_glyph);
}

// 导出字体头文件函数
void export_header(const char *filename, char *chars, int char_count, int w, int h, int outline_width,
                   uint8_t **char_data, int *char_data_len) {
    FILE *f = fopen(filename, "w");
    if (!f) {
        fprintf(stderr, "Error: Cannot open file %s for writing\n", filename);
        return;
    }

    // 生成唯一的头文件宏名
    char macro_name[100];
    snprintf(macro_name, sizeof(macro_name), "FONT_I4_BLACK_WHITE_GRAY_%dx%d_H", w, h);

    fprintf(f, "#ifndef %s\n", macro_name);
    fprintf(f, "#define %s\n\n", macro_name);
    fprintf(f, "#include <stdint.h>\n\n");
    fprintf(f, "// Auto-generated font data\n");
    fprintf(f, "// Font size: %dx%d px, Outline width: %d px\n\n", w, h, outline_width);

    // 生成字符数据
    for (int i = 0; i < char_count; i++) {
        unsigned char c = (unsigned char)chars[i];
        fprintf(f, "static const uint8_t char_%02X_%dx%d_i4[] = {", c, w, h);
        for (int j = 0; j < char_data_len[i]; j++) {
            if (j % 16 == 0) fprintf(f, "\n    ");
            fprintf(f, "0x%02X, ", char_data[i][j]);
        }
        fprintf(f, "\n};\n\n");
    }

    // 生成字体数组
    fprintf(f, "static const bitmap_i4_t i4_%dx%d[%d] = {\n", w, h, char_count);
    for (int i = 0; i < char_count; i++) {
        unsigned char c = (unsigned char)chars[i];
        fprintf(f, "    { %d, %d, char_%02X_%dx%d_i4 }, // '%c'\n",
                w, h, c, w, h, (c >= 32 && c <= 126) ? c : ' ');
    }
    fprintf(f, "};\n\n");

    fprintf(f, "#endif // %s\n", macro_name);
    fclose(f);
}

int main(int argc, char** argv) {
    if (argc < 6) {
        fprintf(stderr, "Usage: %s <font_path> <target_w> <target_h> <outline_width> <chars>\n", argv[0]);
        fprintf(stderr, "Example: %s font.ttf 16 16 0.5 \"ABCDEFGHIJKLMNOPQRSTUVWXYZ\"\n");
        return 1;
    }

    const char* font_path = argv[1];
    int target_w = atoi(argv[2]);
    int target_h = atoi(argv[3]);
    float outline_width = atof(argv[4]);
    char *chars = argv[5];

    FT_Library library;
    FT_Face face;
    FT_Error error;

    // 初始化FreeType
    error = FT_Init_FreeType(&library);
    if (error) {
        fprintf(stderr, "FreeType init error: %d\n", error);
        return 1;
    }

    // 加载字体
    error = FT_New_Face(library, font_path, 0, &face);
    if (error) {
        fprintf(stderr, "Font load error: %d\n", error);
        FT_Done_FreeType(library);
        return 1;
    }

    // 自动计算像素大小
    int pixel_size = auto_calc_pixel_size(face, target_h);

    // 自适应描边宽度
    if (outline_width < 0) {
        outline_width = calculate_outline_width(pixel_size, target_h);
    }

    printf("Using outline width: %.2f\n", outline_width);

    int char_count = strlen(chars);

    // 分配内存
    uint8_t** char_i4_data = (uint8_t**)calloc(char_count, sizeof(uint8_t*));
    int* char_i4_len = (int*)calloc(char_count, sizeof(int));

    if (!char_i4_data || !char_i4_len) {
        fprintf(stderr, "Memory alloc failed\n");
        FT_Done_Face(face);
        FT_Done_FreeType(library);
        return 1;
    }

    // 处理每个字符
    for (int i = 0; i < char_count; i++) {
        unsigned char* buf = NULL;
        GlyphMetrics metrics = {0};

        // 渲染字符
        render_char_with_outline(face, chars[i], &buf, &metrics, outline_width);
        if (!buf) {
            fprintf(stderr, "Render failed for char '%c'\n", chars[i]);
            char_i4_data[i] = NULL;
            char_i4_len[i] = 0;
            continue;
        }

        // 缩放到目标尺寸
        unsigned char* scaled = (unsigned char*)calloc(target_w * target_h, 1);
        if (!scaled) {
            fprintf(stderr, "Memory alloc failed for scaled char '%c'\n", chars[i]);
            free(buf);
            char_i4_data[i] = NULL;
            char_i4_len[i] = 0;
            continue;
        }

        // 特殊字符处理：保持清晰度
        if (chars[i] == '-' || chars[i] == ':' || chars[i] == '.' || chars[i] == ',') {
            // 对特殊字符使用最近邻缩放保持清晰度
            float x_ratio = (float)metrics.width / target_w;
            float y_ratio = (float)metrics.height / target_h;

            for (int y = 0; y < target_h; y++) {
                for (int x = 0; x < target_w; x++) {
                    int src_x = (int)(x * x_ratio);
                    int src_y = (int)(y * y_ratio);

                    if (src_x < metrics.width && src_y < metrics.height) {
                        scaled[y * target_w + x] = buf[src_y * metrics.width + src_x];
                    }
                }
            }
        } else {
            // 普通字符使用双线性缩放
            scale_bitmap(buf, metrics.width, metrics.height, scaled, target_w, target_h);
        }

        // 转换为I4格式
        int padded_w = (target_w + 1) & ~1;
        int i4_len = (padded_w * target_h) / 2;
        uint8_t* i4_buf = (uint8_t*)calloc(i4_len, 1);
        if (!i4_buf) {
            fprintf(stderr, "Memory alloc failed for I4 char '%c'\n", chars[i]);
            free(buf);
            free(scaled);
            char_i4_data[i] = NULL;
            char_i4_len[i] = 0;
            continue;
        }
        convert_to_i4(scaled, i4_buf, target_w, target_h);

        // 保存数据
        char_i4_data[i] = i4_buf;
        char_i4_len[i] = i4_len;

        free(buf);
        free(scaled);
    }

    // 生成输出文件名
    char out_file[256];
    snprintf(out_file, sizeof(out_file), "font_chars_i4_%dx%d.h", target_w, target_h);

    // 导出头文件
    export_header(out_file, chars, char_count, target_w, target_h, (int)(outline_width * 10),
                  char_i4_data, char_i4_len);

    // 清理资源
    for (int i = 0; i < char_count; i++) {
        if (char_i4_data[i]) free(char_i4_data[i]);
    }
    free(char_i4_data);
    free(char_i4_len);

    FT_Done_Face(face);
    FT_Done_FreeType(library);

    printf("Font export complete: %s\n", out_file);
    return 0;
}