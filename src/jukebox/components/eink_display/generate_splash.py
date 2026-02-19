#!/usr/bin/env python3
"""
Generate the default splash.bmp for the e-ink display.

Run once to produce splash.bmp in the same directory:
    python3 generate_splash.py

The image is 250x122 pixels (landscape orientation as expected by show_splash.py).
Replace splash.bmp with any custom 250x122 1-bit image to customise the splash.
"""

import os
from PIL import Image, ImageDraw, ImageFont

W, H = 250, 122
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'splash.bmp')

img = Image.new('1', (W, H), 1)  # white background
draw = ImageDraw.Draw(img)


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def load_font(bold, size):
    paths = (
        ['/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
        if bold else
        ['/usr/share/fonts/truetype/freefont/FreeSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    )
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


font_title = load_font(bold=True, size=28)
font_sub   = load_font(bold=False, size=13)
font_zzz   = load_font(bold=True, size=11)


# ---------------------------------------------------------------------------
# Text (left side)
# ---------------------------------------------------------------------------

draw.text((8, 18), 'Jukebox', font=font_title, fill=0)
draw.text((8, 54), 'Loading...', font=font_sub, fill=0)

# Thin vertical divider
draw.line([(118, 10), (118, H - 10)], fill=0, width=1)


# ---------------------------------------------------------------------------
# Sleeping bunny (right side, centred around x=185, ground y=108)
# ---------------------------------------------------------------------------

BX = 185   # bunny centre x
GY = 108   # ground line y

# Ground line
draw.line([(125, GY), (245, GY)], fill=0, width=1)

# Body — wide ellipse, lying down
draw.ellipse([BX - 38, GY - 28, BX + 38, GY], outline=0, width=2)

# Head — circle sitting on top-right of body
HX, HY = BX + 22, GY - 36
draw.ellipse([HX - 16, HY - 14, HX + 16, HY + 14], outline=0, width=2)

# Ear left — tall upright ellipse
draw.ellipse([HX - 12, HY - 42, HX - 2, HY - 12], outline=0, width=2)

# Ear right — drooped (tilted rectangle approximated as rotated ellipse)
# Approximate with a narrow ellipse offset to the right and lower
draw.ellipse([HX + 2, HY - 36, HX + 14, HY - 8], outline=0, width=2)

# Closed eye — small arc (two short lines forming a gentle curve)
ex, ey = HX - 3, HY - 2
draw.arc([ex - 6, ey - 3, ex + 6, ey + 3], start=200, end=340, fill=0, width=2)

# Nose — tiny dot
draw.ellipse([HX + 3, HY + 3, HX + 6, HY + 6], fill=0)

# Front paw tucked out from body bottom-left
draw.ellipse([BX - 30, GY - 8, BX - 14, GY + 2], outline=0, width=2)

# Tail — small circle on the left end of body
draw.ellipse([BX - 44, GY - 14, BX - 34, GY - 4], outline=0, width=2)

# Zzz floating up from head
draw.text((HX + 14, HY - 52), 'z', font=font_zzz, fill=0)
draw.text((HX + 20, HY - 64), 'z', font=font_zzz, fill=0)
draw.text((HX + 27, HY - 78), 'Z', font=font_zzz, fill=0)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

img.save(OUT)
print(f'Saved: {OUT}  ({W}x{H}, mode={img.mode})')
