"""
E-Ink Display Plugin for Jukebox

Renders jukebox state on a Waveshare 2.13" e-ink display (250x122 pixels).
Subscribes to ZMQ 'playerstatus' topic and updates the display on every state change.

Hardware: Waveshare 2.13inch e-Paper HAT (V4), connected via SPI0 on default pins:
  BUSY=GPIO24, RST=GPIO17, DC=GPIO25, CS=GPIO8(CE0), CLK=GPIO11, DIN=GPIO10

The plugin is guarded by an enable flag in jukebox.yaml:
  eink_display:
    enable: true

Requires: Pillow, waveshare-epaper (epd2in13_V4 driver)
Install: pip install Pillow
         # Clone Waveshare e-Paper library and add to path, or install from PyPI if available
"""

import glob
import logging
import sys
import threading

import jukebox.cfghandler
import jukebox.plugs as plugs
import jukebox.publishing.subscriber

logger = logging.getLogger('jb.eink')
cfg = jukebox.cfghandler.get_handler('jukebox')

# Module-level state
_display_thread: 'DisplayThread | None' = None
_enabled: bool = False


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_status(epd, state: str, title: str, artist: str) -> None:
    """Draw current player status onto the e-ink display.

    :param epd: Initialised EPD driver instance
    :param state: MPD state string: 'play', 'pause', or 'stop'
    :param title: Current track title (may be empty string)
    :param artist: Current track artist (may be empty string)
    """
    from PIL import Image, ImageDraw, ImageFont

    # The display is mounted rotated 90°, so draw in landscape (250×122) then rotate.
    # epd.width=250, epd.height=122 — draw canvas matches driver's native landscape dims.
    draw_w, draw_h = epd.width, epd.height
    image = Image.new('1', (draw_w, draw_h), 255)  # 255 = white background
    draw = ImageDraw.Draw(image)

    try:
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        font_status = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_status = ImageFont.load_default()

    # State icon / label
    state_labels = {'play': '> Playing', 'pause': '|| Paused', 'stop': '[] Stopped'}
    state_text = state_labels.get(state, state.capitalize())
    draw.text((4, 4), state_text, font=font_status, fill=0)

    # Separator line
    draw.line([(0, 24), (draw_w, 24)], fill=0, width=1)

    # Title — truncate if too long
    title_text = title if title else '---'
    if len(title_text) > 28:
        title_text = title_text[:25] + '...'
    draw.text((4, 30), title_text, font=font_large, fill=0)

    # Artist
    artist_text = artist if artist else ''
    if len(artist_text) > 32:
        artist_text = artist_text[:29] + '...'
    draw.text((4, 52), artist_text, font=font_small, fill=0)

    # Rotate 90° clockwise to correct for the physical 90° mounting of the display
    image = image.rotate(-90, expand=True)
    epd.display(epd.getbuffer(image))


def _render_message(epd, line1: str, line2: str = '') -> None:
    """Render a simple one- or two-line text message on the display.

    :param epd: Initialised EPD driver instance
    :param line1: First line of text
    :param line2: Optional second line of text
    """
    from PIL import Image, ImageDraw, ImageFont

    draw_w, draw_h = epd.width, epd.height
    image = Image.new('1', (draw_w, draw_h), 255)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
        font2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    except IOError:
        font = ImageFont.load_default()
        font2 = ImageFont.load_default()

    draw.text((4, 30), line1, font=font, fill=0)
    if line2:
        draw.text((4, 60), line2, font=font2, fill=0)

    # Rotate 90° clockwise to correct for the physical 90° mounting of the display
    image = image.rotate(-90, expand=True)
    epd.display(epd.getbuffer(image))


# ---------------------------------------------------------------------------
# Subscriber thread
# ---------------------------------------------------------------------------

class DisplayThread(threading.Thread):
    """Background thread that subscribes to 'playerstatus' and updates the display."""

    def __init__(self, epd):
        super().__init__(name='EinkDisplay', daemon=True)
        self._epd = epd
        self._keep_running = True
        self._last_state = ''
        self._last_title = ''
        self._last_artist = ''

    def run(self) -> None:
        logger.info('E-Ink display thread started')
        sub = jukebox.publishing.subscriber.Subscriber(
            'inproc://PublisherToProxy', ['playerstatus']
        )
        while self._keep_running:
            try:
                topic, payload = sub.receive()
                if not self._keep_running:
                    break
                if topic == 'playerstatus' and isinstance(payload, dict):
                    state = payload.get('state', 'stop')
                    title = payload.get('title', '')
                    artist = payload.get('artist', '')
                    # Only redraw if something actually changed — e-ink refreshes are slow
                    if state != self._last_state or title != self._last_title or artist != self._last_artist:
                        self._last_state = state
                        self._last_title = title
                        self._last_artist = artist
                        logger.debug(f'E-Ink update: state={state} title={title!r} artist={artist!r}')
                        try:
                            self._epd.init()
                            _render_status(self._epd, state, title, artist)
                            self._epd.sleep()
                        except Exception as e:
                            logger.error(f'E-Ink render error: {e.__class__.__name__}: {e}')
            except Exception as e:
                if self._keep_running:
                    logger.error(f'E-Ink subscriber error: {e.__class__.__name__}: {e}')
        logger.info('E-Ink display thread stopped')

    def stop(self) -> None:
        self._keep_running = False


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
    global _enabled, _display_thread

    _enabled = cfg.setndefault('eink_display', 'enable', value=False)
    if not _enabled:
        logger.info('E-Ink display is disabled in config')
        return

    try:
        # The waveshare-epaper PyPI package installs the library in a nested path
        # that is not automatically on sys.path. Find and add it dynamically.
        _ensure_waveshare_on_path()

        # Try driver versions from newest to oldest — import whichever exists
        epd_module = _import_epd_driver()
        if epd_module is None:
            raise ImportError('No compatible epd2in13 driver found (tried V4, V3, V2)')

        epd = epd_module.EPD()
        epd.init()
        epd.Clear()
        _render_message(epd, 'Jukebox', 'starting...')
        epd.sleep()
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

    _display_thread = DisplayThread(epd)
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
            epd.init()
            _render_message(epd, 'Shutting', 'down...')
            epd.sleep()
        except Exception as e:
            logger.error(f'E-Ink atexit render error: {e.__class__.__name__}: {e}')

    return _display_thread
