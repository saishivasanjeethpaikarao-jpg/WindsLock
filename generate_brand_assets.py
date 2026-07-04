"""Generate Windslock logo and icon assets."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

import brand


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(size: int = 512) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 512

    def xy(values):
        return tuple(int(v * scale) for v in values)

    draw.rounded_rectangle(xy((42, 42, 470, 470)), radius=int(96 * scale), fill=(17, 24, 39, 255))
    draw.rounded_rectangle(xy((78, 82, 434, 430)), radius=int(76 * scale), outline=(34, 197, 94, 255), width=int(18 * scale))
    draw.arc(xy((158, 104, 354, 300)), 180, 360, fill=(241, 245, 249, 255), width=int(34 * scale))
    draw.rounded_rectangle(xy((138, 218, 374, 382)), radius=int(34 * scale), fill=(34, 197, 94, 255))
    draw.ellipse(xy((232, 270, 280, 318)), fill=(17, 24, 39, 255))
    draw.rounded_rectangle(xy((246, 304, 266, 348)), radius=int(8 * scale), fill=(17, 24, 39, 255))
    return image


def make_logo() -> Image.Image:
    width, height = 1400, 420
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    icon = make_icon(320)
    image.alpha_composite(icon, (40, 50))
    title_font = _font(112, bold=True)
    tagline_font = _font(38)
    draw.text((400, 92), brand.APP_NAME, fill=(17, 24, 39, 255), font=title_font)
    draw.text((408, 224), brand.APP_TAGLINE, fill=(51, 65, 85, 255), font=tagline_font)
    draw.rounded_rectangle((408, 292, 820, 342), radius=25, fill=(34, 197, 94, 255))
    draw.text((434, 300), "App lock  Web lock  Folder lock", fill=(17, 24, 39, 255), font=_font(24, bold=True))
    return image


def main() -> None:
    brand.assets_dir().mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.save(brand.icon_ico(), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    icon.save(brand.asset_path("windslock_icon.png"))
    make_logo().save(brand.logo_png())


if __name__ == "__main__":
    main()
