#!/usr/bin/env python3
"""
E-Ink splash screen — shown before the Jukebox daemon starts.

Displays a logo image (or a text fallback) on the Waveshare 2.13" e-ink
display as early visual feedback during boot.

Called via ExecStartPre in jukebox-daemon.service. Runs once and exits.

Usage:
    python3 show_splash.py [image_path]

    image_path: optional path to a BMP/PNG/JPG image to display.
                Must be 250x122 or 122x250 pixels (landscape or portrait).
                Defaults to splash.bmp in the same directory as this script.

If the image is not found or fails to load, a text fallback is shown instead.
"""

import glob
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('eink.splash')

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_IMAGE = os.path.join(_SCRIPT_DIR, '..', '..', '..', '..', 'img', 'Dancing.jpeg')


def _ensure_waveshare_on_path() -> None:
    try:
        import waveshare_epd  # noqa: F401
        return
    except ImportError:
        pass
    for site_pkg in sys.path:
        matches = glob.glob(f'{site_pkg}/**/waveshare_epd', recursive=True)
        if matches:
            parent = str(matches[0]).removesuffix('/waveshare_epd')
            if parent not in sys.path:
                sys.path.insert(0, parent)
                logger.info(f'Added waveshare_epd path: {parent}')
            return
    logger.warning('waveshare_epd not found in any site-packages path')


def _import_epd_driver():
    for version in ('epd2in13_V4', 'epd2in13_V3', 'epd2in13_V2', 'epd2in13'):
        try:
            import importlib
            module = importlib.import_module(f'waveshare_epd.{version}')
            logger.info(f'Loaded driver: waveshare_epd.{version}')
            return module
        except ImportError:
            continue
    return None


def _show_image(epd, image_path: str) -> bool:
    """Display an image file. Returns True on success."""
    from PIL import Image
    try:
        img = Image.open(image_path).convert('1')
    except Exception as e:
        logger.warning(f'Could not open image {image_path!r}: {e}')
        return False

    w, h = img.size
    target_landscape = (epd.height, epd.width)  # (250, 122)

    if (w, h) == target_landscape:
        pass  # already landscape, getbuffer handles rotation
    elif (w, h) == (epd.width, epd.height):
        pass  # portrait, getbuffer accepts this too
    else:
        logger.info(f'Resizing image from {w}x{h} to {target_landscape[0]}x{target_landscape[1]}')
        img = img.resize(target_landscape, Image.LANCZOS)

    epd.display(epd.getbuffer(img))
    return True


def _show_text_fallback(epd) -> None:
    """Show a simple text splash when no image is available."""
    from PIL import Image, ImageDraw, ImageFont

    draw_w, draw_h = epd.height, epd.width  # landscape: 250x122
    image = Image.new('1', (draw_w, draw_h), 255)
    draw = ImageDraw.Draw(image)

    font_paths = [
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    font = None
    for path in font_paths:
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(path, 28)
            font_small = ImageFont.truetype(path.replace('Bold', ''), 14)
            break
        except (IOError, OSError):
            continue
    if font is None:
        from PIL import ImageFont
        font = ImageFont.load_default()
        font_small = font

    draw.text((4, 20), 'Jukebox', font=font, fill=0)
    draw.text((4, 62), 'Loading...', font=font_small, fill=0)

    # Simple animated dots suggestion — three dots drawn as filled circles
    for i, cx in enumerate([180, 198, 216]):
        r = 5
        draw.ellipse([cx - r, 90 - r, cx + r, 90 + r], fill=0)

    epd.display(epd.getbuffer(image))


def main() -> None:
    image_path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_IMAGE

    _ensure_waveshare_on_path()

    epd_module = _import_epd_driver()
    if epd_module is None:
        logger.error('No compatible EPD driver found — skipping splash')
        sys.exit(0)  # non-fatal: jukebox must still start

    try:
        epd = epd_module.EPD()
        epd.init()
        epd.Clear()

        if not _show_image(epd, image_path):
            logger.info('Falling back to text splash')
            _show_text_fallback(epd)

        # Leave display awake — the jukebox plugin will take over from here.
        # Do NOT call epd.sleep() so the image stays visible during boot.
        logger.info('Splash displayed')
    except Exception as e:
        logger.error(f'Splash failed: {e.__class__.__name__}: {e}')
        sys.exit(0)  # non-fatal


if __name__ == '__main__':
    main()
