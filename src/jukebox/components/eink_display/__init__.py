"""
E-Ink Display Plugin for Jukebox

Renders jukebox state on a Waveshare 2.13" e-ink display in landscape orientation.
The panel is natively portrait (epd.width=122, epd.height=250). Images are created
as landscape (250x122) and the driver's getbuffer() handles the rotation internally.
Subscribes to ZMQ 'playerstatus' topic and updates the display on every state change.

Refresh strategy
----------------
- First render after startup: full init + displayPartBaseImage + displayPartial
  (seeds both old/new RAM buffers so the controller knows what changed)
- Subsequent state/title/artist changes: displayPartial only
  (fast, flicker-free — only changed pixels are driven)
- Every FULL_REFRESH_INTERVAL updates: full init + display + re-seed base image
  (prevents ghosting buildup on the panel)
- Display stays awake between updates; sleep() is called only on long inactivity
  or shutdown.

Hardware: Waveshare 2.13inch e-Paper HAT (V4), connected via SPI0 on default pins:
  BUSY=GPIO24, RST=GPIO17, DC=GPIO25, CS=GPIO8(CE0), CLK=GPIO11, DIN=GPIO10

The plugin is guarded by an enable flag in jukebox.yaml:
  eink_display:
    enable: true
    locale: en        # 'en' (default) or 'uk' for Ukrainian
    show_ip_after_stop_sec: 60

Supported locales: en, uk

Requires: Pillow, waveshare-epaper (epd2in13_V4 driver)
Install: pip install -r src/jukebox/components/eink_display/requirements.txt

Ukrainian locale requires a Cyrillic-capable font. Recommended:
  sudo apt install fonts-freefont-ttf
"""

import glob
import logging
import os
import sys
import threading
import time

import jukebox.cfghandler
import jukebox.plugs as plugs
import jukebox.publishing.subscriber
import zmq

# Paths to bunny images relative to the repo root (resolved at runtime)
_IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', '..', '..', '..', 'img')
_IMG_SLEEP   = os.path.join(_IMG_DIR, 'Dancing.jpeg')
_IMG_GOODBYE = os.path.join(_IMG_DIR, 'GoodBye.jpeg')

logger = logging.getLogger('jb.eink')
cfg = jukebox.cfghandler.get_handler('jukebox')

# How many partial refreshes before forcing a full refresh to clear ghosting.
FULL_REFRESH_INTERVAL = 20

# Module-level state
_display_thread: 'DisplayThread | None' = None
_enabled: bool = False

# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------

# Translations keyed by locale code.
# Each entry has: play/pause/stop state labels and the no_title fallback.
_STRINGS = {
    'en': {
        'play':         'Playing',
        'pause':        'Paused',
        'stop':         'Stopped',
        'no_title':     '---',
        'unknown_card': 'Unknown card',
    },
    'uk': {
        'play':         'Грає',
        'pause':        'Пауза',
        'stop':         'Зупинено',
        'no_title':     '---',
        'unknown_card': 'Невідома картка',
    },
}

# Fonts with Cyrillic support (tried in order, first match wins)
_CYRILLIC_FONTS = [
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
_CYRILLIC_FONTS_BOLD = [
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]

# Module-level locale (set during initialize)
_locale: str = 'en'


def _strings() -> dict:
    """Return the string table for the active locale, falling back to 'en'."""
    return _STRINGS.get(_locale, _STRINGS['en'])


def _load_font(bold: bool, size: int):
    """Load the best available font for the active locale.

    For 'uk' and other non-Latin locales, prefers fonts with Cyrillic coverage.
    Falls back to PIL default font if nothing is found.

    :param bold: Whether to prefer a bold variant
    :param size: Font size in points
    :returns: An ImageFont instance
    """
    from PIL import ImageFont

    candidates = _CYRILLIC_FONTS_BOLD if bold else _CYRILLIC_FONTS
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Icon drawing
# ---------------------------------------------------------------------------

def _draw_state_icon(draw, state: str, x: int, y: int, size: int = 16) -> int:
    """Draw a play/pause/stop icon using PIL primitives at position (x, y).

    No font required — shapes are drawn directly so any font will work.

    :param draw: ImageDraw instance
    :param state: 'play', 'pause', or 'stop'
    :param x: Left edge of the icon bounding box
    :param y: Top edge of the icon bounding box
    :param size: Icon height/width in pixels (default 16)
    :returns: x coordinate immediately after the icon (for text placement)
    """
    if state == 'play':
        # Filled right-pointing triangle
        mid_y = y + size // 2
        draw.polygon([(x, y), (x, y + size), (x + size, mid_y)], fill=0)
    elif state == 'pause':
        # Two vertical filled rectangles
        bar_w = max(3, size // 4)
        gap = max(2, size // 4)
        draw.rectangle([x, y, x + bar_w, y + size], fill=0)
        draw.rectangle([x + bar_w + gap, y, x + bar_w * 2 + gap, y + size], fill=0)
    else:
        # Filled square for stop (and any unknown state)
        draw.rectangle([x, y, x + size, y + size], fill=0)
    return x + size + 5  # 5px gap between icon and text


def _draw_wifi_icon(draw, x: int, y: int, size: int = 14) -> None:
    """Draw a Wi-Fi icon (three curved arcs) at position (x, y).

    The icon is drawn as a simplified Wi-Fi symbol with three nested arcs.

    :param draw: ImageDraw instance
    :param x: Left edge of the icon bounding box
    :param y: Top edge of the icon bounding box
    :param size: Icon height in pixels (default 14)
    """
    # Wi-Fi icon: bottom dot + 3 arcs above it
    # Bottom dot (access point)
    dot_r = max(1, size // 8)
    cx = x + size // 2
    dot_y = y + size - dot_r
    draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=0)

    # Three arcs (small, medium, large) — drawn as partial circles
    # Using arc() requires PIL to be built with freetype, so use line segments instead
    arc_w = max(1, size // 10)
    for i, radius in enumerate([size // 4, size // 2, 3 * size // 4]):
        y_offset = y + size - radius
        draw.arc([cx - radius, y_offset, cx + radius, y_offset + radius * 2], start=200, end=340, fill=0, width=arc_w)


def _draw_bluetooth_icon(draw, x: int, y: int, size: int = 14) -> None:
    """Draw a Bluetooth icon (stylised 'B' symbol) at position (x, y).

    The icon is drawn as a simplified Bluetooth rune symbol.

    :param draw: ImageDraw instance
    :param x: Left edge of the icon bounding box
    :param y: Top edge of the icon bounding box
    :param size: Icon height in pixels (default 14)
    """
    # Bluetooth icon: vertical line with two triangular shapes
    cx = x + size // 2
    line_w = max(1, size // 10)

    # Vertical center line
    draw.line([(cx, y), (cx, y + size)], fill=0, width=line_w)

    # Upper triangle (pointing right-up)
    mid_y = y + size // 2
    draw.polygon([(cx, y), (x + size, mid_y - size // 6), (cx, mid_y)], outline=0, fill=0)

    # Lower triangle (pointing right-down)
    draw.polygon([(cx, mid_y), (x + size, mid_y + size // 6), (cx, y + size)], outline=0, fill=0)


# ---------------------------------------------------------------------------
# Image builders
# ---------------------------------------------------------------------------

def _build_status_image(epd,
                        state: str,
                        title: str,
                        artist: str,
                        wifi: bool = False,
                        bluetooth: bool = False,
                        status_text_override: str = ''):
    """Build and return a PIL Image for the current player status.

    Does not touch the display — callers decide whether to do a full or
    partial refresh.

    :param epd: Initialised EPD driver instance (used for dimensions only)
    :param state: MPD state string: 'play', 'pause', or 'stop'
    :param title: Current track title (may be empty string)
    :param artist: Current track artist (may be empty string)
    :param wifi: Whether Wi-Fi is connected (shows icon if True)
    :param bluetooth: Whether Bluetooth is connected (shows icon if True)
    :param status_text_override: Optional replacement for the status-bar label text.
        The state icon remains based on ``state``.
    :returns: PIL Image in landscape orientation (250×122)
    """
    from PIL import Image, ImageDraw

    # epd.width=122, epd.height=250 (portrait panel native).
    # Draw in landscape (250×122): use (epd.height, epd.width) as canvas size.
    # getbuffer() detects the landscape dims and auto-rotates 90° internally.
    draw_w, draw_h = epd.height, epd.width
    image = Image.new('1', (draw_w, draw_h), 255)  # 255 = white background
    draw = ImageDraw.Draw(image)

    font_large = _load_font(bold=True, size=24)
    font_small = _load_font(bold=False, size=16)
    font_status = _load_font(bold=True, size=18)

    s = _strings()

    # Layout (landscape 250×122):
    #   y=2   status label  (18pt, ~22px tall) → bottom ~24
    #   y=26  separator line
    #   y=30  title         (24pt, ~29px tall) → bottom ~59
    #   y=64  artist        (16pt, ~20px tall) → bottom ~84

    max_text_w = draw_w - 8  # 4px padding each side

    # State icon + label — icon drawn as PIL primitives, text placed after it
    icon_size = font_status.size if hasattr(font_status, 'size') else 18
    text_x = _draw_state_icon(draw, state, x=4, y=2, size=icon_size)
    state_text = status_text_override if status_text_override else s.get(state, state.capitalize())
    draw.text((text_x, 2), state_text, font=font_status, fill=0)

    # Connectivity icons in top-right corner
    conn_icon_size = 14
    conn_x = draw_w - 4  # Start from right edge with 4px padding
    if bluetooth:
        conn_x -= conn_icon_size
        _draw_bluetooth_icon(draw, conn_x, 4, conn_icon_size)
        conn_x -= 4  # 4px gap between icons
    if wifi:
        conn_x -= conn_icon_size
        _draw_wifi_icon(draw, conn_x, 4, conn_icon_size)

    # Separator line
    draw.line([(0, 26), (draw_w, 26)], fill=0, width=1)

    # Title — truncate by pixel width so it fits regardless of font metrics
    title_text = title if title else s['no_title']
    while title_text and draw.textlength(title_text, font=font_large) > max_text_w:
        title_text = title_text[:-1]
    if title_text != (title if title else s['no_title']):
        title_text = title_text[:-3] + '...' if len(title_text) >= 3 else title_text
    draw.text((4, 30), title_text, font=font_large, fill=0)

    # Artist — same pixel-width truncation
    artist_text = artist if artist else ''
    while artist_text and draw.textlength(artist_text, font=font_small) > max_text_w:
        artist_text = artist_text[:-1]
    if artist_text != artist:
        artist_text = artist_text[:-3] + '...' if len(artist_text) >= 3 else artist_text
    draw.text((4, 64), artist_text, font=font_small, fill=0)

    return image



# ---------------------------------------------------------------------------
# Bunny image loader
# ---------------------------------------------------------------------------

def _build_bunny_image(epd, image_path: str):
    """Load a bunny JPEG, convert to 1-bit, and centre it on the landscape canvas.

    The source images are 122px tall (matching epd.width) but narrower than
    250px, so they are centred horizontally with white padding on each side.
    Falls back to _build_message_image if the file cannot be opened.

    :param epd: Initialised EPD driver instance (used for dimensions)
    :param image_path: Absolute path to the JPEG file
    :returns: PIL Image in landscape orientation (250×122)
    """
    from PIL import Image

    draw_w, draw_h = epd.height, epd.width  # landscape: 250×122
    canvas = Image.new('1', (draw_w, draw_h), 1)  # white background

    try:
        src = Image.open(image_path).convert('1')
        sw, sh = src.size
        # Scale to fit height if needed, preserving aspect ratio
        if sh != draw_h:
            scale = draw_h / sh
            sw, sh = int(sw * scale), draw_h
            src = src.resize((sw, sh), Image.LANCZOS)
        # Centre horizontally
        x_off = (draw_w - sw) // 2
        canvas.paste(src, (x_off, 0))
    except Exception as e:
        logger.warning(f'Could not load bunny image {image_path!r}: {e}')

    return canvas


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _full_refresh(epd, image) -> None:
    """Full-panel refresh: init → display → seed both RAM buffers for partial.

    Use for the first render and every FULL_REFRESH_INTERVAL updates.
    Leaves the display awake and ready for subsequent partial refreshes.

    :param epd: Initialised EPD driver instance
    :param image: PIL Image in landscape orientation (250×122)
    """
    buf = epd.getbuffer(image)
    epd.init()
    epd.display(buf)
    # Seed the "old frame" buffer so displayPartial can diff against it
    epd.displayPartBaseImage(buf)


def _partial_refresh(epd, image) -> None:
    """Partial refresh: only drives pixels that changed since last base image.

    Fast and flicker-free. Display must have been seeded with displayPartBaseImage
    at least once before calling this.

    :param epd: Initialised EPD driver instance
    :param image: PIL Image in landscape orientation (250×122)
    """
    epd.displayPartial(epd.getbuffer(image))


# ---------------------------------------------------------------------------
# Subscriber thread
# ---------------------------------------------------------------------------

class DisplayThread(threading.Thread):
    """Background thread that subscribes to 'playerstatus' and 'host.connectivity', updates the display.

    Refresh strategy:
    - First render: full refresh (init + display + seed base image)
    - Subsequent renders: partial refresh (fast, flicker-free)
    - Every FULL_REFRESH_INTERVAL renders: forced full refresh to clear ghosting
    - Display stays awake between updates
    """

    def __init__(self, epd, show_ip_after_stop_sec: int = 60):
        super().__init__(name='EinkDisplay', daemon=True)
        self._epd = epd
        self._keep_running = True
        self._last_state = ''
        self._last_title = ''
        self._last_artist = ''
        self._last_wifi = False
        self._last_bluetooth = False
        self._render_count = 0  # tracks when to force a full refresh
        self._show_ip_after_stop_sec = max(0, int(show_ip_after_stop_sec))
        self._stopped_since = None
        self._status_text_override = ''
        self._cached_ip = ''
        self._last_ip_fetch = 0.0
        self._ip_refresh_interval_sec = 10.0
        self._unknown_card_id = ''
        self._unknown_card_shown_at = 0.0
        self._unknown_card_display_sec = 10

    def run(self) -> None:
        logger.info('E-Ink display thread started')
        sub = jukebox.publishing.subscriber.Subscriber(
            'inproc://PublisherToProxy', ['playerstatus', 'host.connectivity', 'rfid.card_id_unknown']
        )
        # Wake up periodically so stop-timeout transitions can trigger render updates.
        sub.socket.setsockopt(zmq.RCVTIMEO, 1000)
        while self._keep_running:
            try:
                try:
                    topic, payload = sub.receive()
                except zmq.Again:
                    topic, payload = None, None
                if not self._keep_running:
                    break

                changed = False

                if topic == 'playerstatus' and isinstance(payload, dict):
                    state = payload.get('state', 'stop')
                    title = payload.get('title', '')
                    artist = payload.get('artist', '')
                    if state != self._last_state:
                        if state == 'stop':
                            self._stopped_since = time.monotonic()
                        else:
                            self._stopped_since = None
                    if (state != self._last_state
                            or title != self._last_title
                            or artist != self._last_artist):
                        self._last_state = state
                        self._last_title = title
                        self._last_artist = artist
                        self._unknown_card_id = ''
                        changed = True
                        logger.debug(
                            f'E-Ink player update: state={state} title={title!r} artist={artist!r}'
                        )

                elif topic == 'rfid.card_id_unknown' and isinstance(payload, str):
                    self._unknown_card_id = payload
                    self._unknown_card_shown_at = time.monotonic()
                    changed = True
                    logger.debug(f'E-Ink unknown card: {payload!r}')

                elif topic == 'host.connectivity' and isinstance(payload, dict):
                    wifi = payload.get('wifi', False)
                    bluetooth = payload.get('bluetooth', False)
                    if (wifi != self._last_wifi or bluetooth != self._last_bluetooth):
                        self._last_wifi = wifi
                        self._last_bluetooth = bluetooth
                        changed = True
                        logger.debug(f'E-Ink connectivity update: wifi={wifi} bluetooth={bluetooth}')

                if self._update_status_text_override():
                    changed = True
                if self._expire_unknown_card():
                    changed = True

                if changed:
                    if self._unknown_card_id:
                        s = _strings()
                        self._render(self._last_state, self._unknown_card_id, '',
                                     self._last_wifi, self._last_bluetooth,
                                     status_text_override=s['unknown_card'])
                    else:
                        self._render(self._last_state, self._last_title, self._last_artist,
                                     self._last_wifi, self._last_bluetooth, self._status_text_override)

            except Exception as e:
                if self._keep_running:
                    logger.error(f'E-Ink subscriber error: {e.__class__.__name__}: {e}')
        logger.info('E-Ink display thread stopped')

    def _fetch_ip_cached(self) -> str:
        """Read host IP with throttling to avoid subprocess calls on every loop."""
        now = time.monotonic()
        if (now - self._last_ip_fetch) < self._ip_refresh_interval_sec:
            return self._cached_ip

        self._last_ip_fetch = now
        ip = plugs.call_ignore_errors('host', 'get_ip_address')
        self._cached_ip = ip.strip() if isinstance(ip, str) else ''
        return self._cached_ip

    def _update_status_text_override(self) -> bool:
        """Switch status text from 'Stopped' to IP after configured idle timeout."""
        old_text = self._status_text_override
        new_text = ''

        if (self._last_state == 'stop'
                and self._stopped_since is not None
                and self._show_ip_after_stop_sec > 0):
            stopped_for = time.monotonic() - self._stopped_since
            if stopped_for >= self._show_ip_after_stop_sec:
                new_text = self._fetch_ip_cached()

        self._status_text_override = new_text
        return new_text != old_text

    def _expire_unknown_card(self) -> bool:
        """Clear unknown card display after the timeout elapses.

        :returns: True if the state changed (card display was cleared).
        """
        if self._unknown_card_id:
            if (time.monotonic() - self._unknown_card_shown_at) >= self._unknown_card_display_sec:
                self._unknown_card_id = ''
                return True
        return False

    def _render(self,
                state: str,
                title: str,
                artist: str,
                wifi: bool,
                bluetooth: bool,
                status_text_override: str = '') -> None:
        """Render one frame, choosing full or partial refresh as appropriate."""
        try:
            image = _build_status_image(self._epd,
                                        state,
                                        title,
                                        artist,
                                        wifi,
                                        bluetooth,
                                        status_text_override=status_text_override)
            use_full = (self._render_count % FULL_REFRESH_INTERVAL == 0)
            if use_full:
                logger.debug(f'E-Ink full refresh (count={self._render_count})')
                _full_refresh(self._epd, image)
            else:
                logger.debug(f'E-Ink partial refresh (count={self._render_count})')
                _partial_refresh(self._epd, image)
            self._render_count += 1
        except Exception as e:
            logger.error(f'E-Ink render error: {e.__class__.__name__}: {e}')

    def stop(self) -> None:
        self._keep_running = False
        # Put the display to sleep when the thread is stopping
        try:
            self._epd.sleep()
        except Exception as e:
            logger.error(f'E-Ink sleep error: {e.__class__.__name__}: {e}')


# ---------------------------------------------------------------------------
# Driver import helpers
# ---------------------------------------------------------------------------

def _ensure_waveshare_on_path() -> None:
    """Add the waveshare_epd library directory to sys.path if not already importable.

    The waveshare-epaper PyPI package installs files under a deeply nested path
    (site-packages/epaper/e-Paper/RaspberryPi_JetsonNano/python/lib/) that is
    not on sys.path by default. Find it via glob and add it once.
    """
    try:
        import waveshare_epd  # noqa: F401 — already importable, nothing to do
        return
    except ImportError:
        pass

    # Search all site-packages for the waveshare_epd directory
    for site_pkg in sys.path:
        matches = glob.glob(f'{site_pkg}/**/waveshare_epd', recursive=True)
        if matches:
            parent = str(matches[0]).removesuffix('/waveshare_epd')
            if parent not in sys.path:
                sys.path.insert(0, parent)
                logger.info(f'Added waveshare_epd path: {parent}')
            return

    logger.warning('waveshare_epd directory not found in any site-packages path')


def _import_epd_driver():
    """Import the best available epd2in13 driver, trying V4 → V3 → V2.

    :returns: The imported driver module, or None if none found.
    """
    for version in ('epd2in13_V4', 'epd2in13_V3', 'epd2in13_V2', 'epd2in13'):
        try:
            import importlib
            module = importlib.import_module(f'waveshare_epd.{version}')
            logger.info(f'Loaded Waveshare driver: waveshare_epd.{version}')
            return module
        except ImportError:
            continue
    return None


# ---------------------------------------------------------------------------
# Plugin lifecycle
# ---------------------------------------------------------------------------

@plugs.initialize
def initialize() -> None:
    """Load the EPD driver, initialise the display, and show the boot message."""
    global _enabled, _display_thread, _locale

    _enabled = cfg.setndefault('eink_display', 'enable', value=False)
    if not _enabled:
        logger.info('E-Ink display is disabled in config')
        return

    _locale = cfg.setndefault('eink_display', 'locale', value='en')
    if _locale not in _STRINGS:
        logger.warning(f"E-Ink unsupported locale '{_locale}', falling back to 'en'")
        _locale = 'en'
    logger.info(f'E-Ink display locale: {_locale}')

    stop_ip_after_sec = cfg.setndefault('eink_display', 'show_ip_after_stop_sec', value=60)
    try:
        stop_ip_after_sec = max(0, int(stop_ip_after_sec))
    except (TypeError, ValueError):
        logger.warning(f"Invalid eink_display.show_ip_after_stop_sec={stop_ip_after_sec!r}, using 60")
        stop_ip_after_sec = 60
    globals()['_stop_ip_after_sec'] = stop_ip_after_sec
    logger.info(f'E-Ink stop-to-IP timeout: {stop_ip_after_sec}s')

    try:
        _ensure_waveshare_on_path()

        epd_module = _import_epd_driver()
        if epd_module is None:
            raise ImportError('No compatible epd2in13 driver found (tried V4, V3, V2)')

        epd = epd_module.EPD()
        epd.init()
        epd.Clear()

        # Show sleeping bunny during boot; seed the base image so the
        # display thread can start with partial refreshes immediately.
        boot_image = _build_bunny_image(epd, _IMG_SLEEP)
        buf = epd.getbuffer(boot_image)
        epd.display(buf)
        epd.displayPartBaseImage(buf)

        # Store on module for use by finalize / atexit
        globals()['_epd'] = epd
        logger.info('E-Ink display initialised')
    except Exception as e:
        logger.error(f'E-Ink display init failed: {e.__class__.__name__}: {e}')
        _enabled = False


@plugs.finalize
def finalize() -> None:
    """Start the subscriber thread now that ZMQ inproc transport is available."""
    global _display_thread

    if not _enabled:
        return

    epd = globals().get('_epd')
    if epd is None:
        return

    stop_ip_after_sec = globals().get('_stop_ip_after_sec', 60)
    _display_thread = DisplayThread(epd, show_ip_after_stop_sec=stop_ip_after_sec)
    _display_thread.start()
    logger.info('E-Ink display subscriber thread started')


@plugs.atexit
def atexit(**ignored_kwargs):
    """Show shutdown message and clean up the display."""
    global _display_thread

    if not _enabled:
        return None

    if _display_thread is not None:
        _display_thread.stop()

    epd = globals().get('_epd')
    if epd is not None:
        try:
            goodbye_image = _build_bunny_image(epd, _IMG_GOODBYE)
            # Full refresh for shutdown — display may have been sleeping
            epd.init()
            epd.display(epd.getbuffer(goodbye_image))
            epd.sleep()
        except Exception as e:
            logger.error(f'E-Ink atexit render error: {e.__class__.__name__}: {e}')

    return _display_thread
