"""
Text To Image with Alpha - ComfyUI Custom Node
"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import glob

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fonts")


def get_available_fonts():
    fonts = {}
    if os.path.exists(FONTS_DIR):
        try:
            from fontTools import ttLib
            has_fonttools = True
        except ImportError:
            has_fonttools = False

        for ext in ["*.ttf", "*.otf", "*.TTF", "*.OTF"]:
            for font_file in glob.glob(os.path.join(FONTS_DIR, ext)):
                display_name = None
                if has_fonttools:
                    try:
                        f = ttLib.TTFont(font_file, fontNumber=0, lazy=True)
                        korean_name = None
                        english_name = None
                        if 'name' in f:
                            for record in f['name'].names:
                                if record.nameID == 1:
                                    if record.langID == 0x0412:
                                        korean_name = record.toUnicode()
                                    elif record.platformID == 3 and record.langID == 1033:
                                        english_name = record.toUnicode()
                        display_name = korean_name or english_name
                    except Exception:
                        pass

                if not display_name:
                    display_name = os.path.splitext(os.path.basename(font_file))[0]

                key = display_name
                count = 1
                while key in fonts:
                    count += 1
                    key = f"{display_name} ({count})"
                fonts[key] = font_file

    if not fonts:
        fonts["default"] = "default"

    return fonts


_FONT_MAP = get_available_fonts()
_FONT_NAMES = sorted(_FONT_MAP.keys())


def load_font(font_name: str, font_size: int):
    font_path = _FONT_MAP.get(font_name, "default")
    if font_path != "default" and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=font_size)
    except Exception:
        return ImageFont.load_default()


def hex_to_rgba(hex_color: str, alpha: int = 255):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    else:
        r, g, b = 0, 0, 0
    return (r, g, b, alpha)


def draw_text_with_stroke(draw, pos, text, font, text_color, stroke_color, stroke_width):
    x, y = pos
    if stroke_width > 0:
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    draw.text((x, y), text, font=font, fill=text_color)


class TextToImageAlpha:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True,
                    "default": "안녕하세요\nHello World!",
                    "dynamicPrompts": False,
                }),
                "font": (_FONT_NAMES, ),
                "font_size": ("INT", {"default": 64, "min": 8, "max": 512, "step": 1}),
                "text_color": ("STRING", {"default": "#000000"}),
                "text_alpha": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
                "bg_color": ("STRING", {"default": "#ffffff"}),
                "bg_alpha": ("INT", {"default": 0, "min": 0, "max": 255, "step": 1}),
                "stroke_width": ("INT", {"default": 0, "min": 0, "max": 40, "step": 1}),
                "stroke_color": ("STRING", {"default": "#ffffff"}),
                "stroke_alpha": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
                "padding_x": ("INT", {"default": 16, "min": 0, "max": 512, "step": 1}),
                "padding_y": ("INT", {"default": 16, "min": 0, "max": 512, "step": 1}),
                "line_spacing": ("FLOAT", {"default": 1.2, "min": 0.5, "max": 3.0, "step": 0.1}),
                "h_align": (["left", "center", "right"], {"default": "left"}),
                "v_align": (["top", "center", "bottom"], {"default": "top"}),
                "offset_x": ("INT", {"default": 0, "min": -4096, "max": 4096, "step": 1}),
                "offset_y": ("INT", {"default": 0, "min": -4096, "max": 4096, "step": 1}),
                "supersampling": ("INT", {"default": 2, "min": 1, "max": 4, "step": 1}),
                "width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "render"
    CATEGORY = "image/text"

    def render(
        self,
        text, font, font_size,
        text_color, text_alpha,
        bg_color, bg_alpha,
        stroke_width, stroke_color, stroke_alpha,
        padding_x, padding_y,
        line_spacing,
        h_align, v_align,
        offset_x, offset_y,
        supersampling,
        width=0, height=0,
    ):
        scale = supersampling
        scaled_font_size = font_size * scale
        scaled_px = padding_x * scale
        scaled_py = padding_y * scale
        scaled_stroke = stroke_width * scale
        scaled_ox = offset_x * scale
        scaled_oy = offset_y * scale

        t_color = hex_to_rgba(text_color, text_alpha)
        b_color = hex_to_rgba(bg_color, bg_alpha)
        s_color = hex_to_rgba(stroke_color, stroke_alpha)

        loaded_font = load_font(font, scaled_font_size)
        lines = text.split("\n")

        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)

        line_sizes = []
        for line in lines:
            bbox = dummy_draw.textbbox((0, 0), line if line else " ", font=loaded_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_sizes.append((w, h))

        if not line_sizes:
            line_sizes = [(100 * scale, scaled_font_size)]

        max_line_w = max(s[0] for s in line_sizes)
        single_line_h = max(s[1] for s in line_sizes)
        line_gap = int(single_line_h * line_spacing)
        total_text_h = line_gap * (len(lines) - 1) + single_line_h

        canvas_w = (width * scale) if width > 0 else (max_line_w + scaled_px * 2 + scaled_stroke * 2)
        canvas_h = (height * scale) if height > 0 else (total_text_h + scaled_py * 2 + scaled_stroke * 2)

        img = Image.new("RGBA", (canvas_w, canvas_h), b_color)
        draw = ImageDraw.Draw(img)

        if v_align == "top":
            base_y = scaled_py + scaled_stroke
        elif v_align == "center":
            base_y = (canvas_h - total_text_h) // 2
        else:
            base_y = canvas_h - total_text_h - scaled_py - scaled_stroke

        for i, (line, (lw, lh)) in enumerate(zip(lines, line_sizes)):
            y = base_y + i * line_gap + scaled_oy
            if h_align == "left":
                x = scaled_px + scaled_stroke + scaled_ox
            elif h_align == "center":
                x = (canvas_w - lw) // 2 + scaled_ox
            else:
                x = canvas_w - lw - scaled_px - scaled_stroke + scaled_ox

            draw_text_with_stroke(
                draw=draw, pos=(x, y), text=line, font=loaded_font,
                text_color=t_color, stroke_color=s_color, stroke_width=scaled_stroke,
            )

        final_w = max(1, canvas_w // scale)
        final_h = max(1, canvas_h // scale)
        img = img.resize((final_w, final_h), Image.LANCZOS)

        r, g, b, a = img.split()
        mask_np = np.array(a).astype(np.float32) / 255.0
        mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)

        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np).unsqueeze(0)

        return (img_tensor, mask_tensor)


NODE_CLASS_MAPPINGS = {
    "nambaksa_text_to_image": TextToImageAlpha,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "nambaksa_text_to_image": "Text To Image (Alpha)",
}