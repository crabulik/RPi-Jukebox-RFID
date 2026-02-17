#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Waveshare 2.13" e-Paper HAT display daemon for Phoniebox."""

import logging
import signal
import sys
import time
from enum import Enum

from mpd import MPDClient
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V4

# ── Configuration ─────────────────────────────────────────────────────
MPD_HOST = "localhost"
MPD_PORT = 6600
MPD_TIMEOUT = 0.3
POLL_INTERVAL = 2.0
FULL_REFRESH_INTERVAL = 1800  # 30 minutes

# Display geometry (2.13" V4: 250x122 pixels, landscape)
EPD_WIDTH = 250
EPD_HEIGHT = 122

# Fonts — DejaVu is pre-installed on Raspberry Pi OS
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SIZE_TITLE = 22
FONT_SIZE_ARTIST = 16

MARGIN_X = 10
TITLE_Y = 25
ARTIST_Y = 65

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s'
)
logger = logging.getLogger("eink_display")


class DisplayState(Enum):
    INITIALIZING = "initializing"
    IDLE = "idle"
    SONG_INFO = "song_info"


class EinkDisplay:
    def __init__(self):
        self.epd = None
        self.client = None

        self._current_state = None
        self._current_content = {}
        self._last_full_refresh_time = 0

        self.font_title = ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE_TITLE)
        self.font_artist = ImageFont.truetype(FONT_PATH, FONT_SIZE_ARTIST)

    # ── Display hardware ──────────────────────────────────────────

    def init_display(self):
        """Initialize e-Paper display hardware."""
        self.epd = epd2in13_V4.EPD()
        self.epd.init()
        self.epd.Clear(0xFF)
        self._last_full_refresh_time = time.time()

    def shutdown_display(self):
        """Clear display and enter sleep mode."""
        if self.epd:
            try:
                self.epd.init()
                self.epd.Clear(0xFF)
                self.epd.sleep()
            except Exception:
                logger.exception("Error during display shutdown")

    # ── MPD connection ────────────────────────────────────────────

    def connect_mpd(self):
        """Connect to MPD. Returns True on success."""
        try:
            self.client = MPDClient()
            self.client.timeout = MPD_TIMEOUT
            self.client.connect(MPD_HOST, MPD_PORT)
            return True
        except Exception:
            logger.warning("Could not connect to MPD")
            self.client = None
            return False

    def poll_mpd(self):
        """Poll MPD state. Returns (DisplayState, content_dict).

        Reconnects on failure following the i2c_lcd.py pattern.
        """
        try:
            self.client.ping()
            status = self.client.status()
            current_song = self.client.currentsong()
        except Exception:
            try:
                self.client = MPDClient()
                self.client.timeout = MPD_TIMEOUT
                self.client.connect(MPD_HOST, MPD_PORT)
                status = self.client.status()
                current_song = self.client.currentsong()
            except Exception:
                return DisplayState.IDLE, {}

        mpd_state = status.get('state', 'stop')

        if mpd_state in ('play', 'pause'):
            return self._extract_song_info(current_song)

        # MPD stopped — show song info if a track is queued
        if mpd_state == 'stop' and current_song:
            title = current_song.get('title', '')
            if title:
                return self._extract_song_info(current_song)

        return DisplayState.IDLE, {}

    def _extract_song_info(self, current_song):
        """Extract title and artist from MPD current song dict."""
        title = current_song.get('title', '')
        artist = current_song.get(
            'artist', current_song.get('name', '')
        )
        return DisplayState.SONG_INFO, {
            'title': title, 'artist': artist
        }

    # ── Rendering ─────────────────────────────────────────────────

    def _create_image(self):
        """Create a blank white image matching display dimensions."""
        return Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)

    def _render_centered_text(self, text):
        """Render a single line of large centered text. Always full refresh."""
        image = self._create_image()
        draw = ImageDraw.Draw(image)
        bbox = draw.textbbox((0, 0), text, font=self.font_title)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (EPD_WIDTH - text_w) // 2
        y = (EPD_HEIGHT - text_h) // 2
        draw.text((x, y), text, font=self.font_title, fill=0)
        self._display_image(image, full_refresh=True)

    def _render_song_info(self, title, artist):
        """Render song title and artist in a two-line layout."""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        title = self._truncate_text(
            title, self.font_title, EPD_WIDTH - 2 * MARGIN_X
        )
        artist = self._truncate_text(
            artist, self.font_artist, EPD_WIDTH - 2 * MARGIN_X
        )

        draw.text(
            (MARGIN_X, TITLE_Y), title,
            font=self.font_title, fill=0
        )
        if artist:
            draw.text(
                (MARGIN_X, ARTIST_Y), artist,
                font=self.font_artist, fill=0
            )

        needs_full = (
            time.time() - self._last_full_refresh_time
            >= FULL_REFRESH_INTERVAL
        )
        self._display_image(image, full_refresh=needs_full)

    def _display_image(self, image, full_refresh=False):
        """Send image to the e-Paper display."""
        if full_refresh:
            self.epd.init()
            self.epd.display(self.epd.getbuffer(image))
            self._last_full_refresh_time = time.time()
        else:
            self.epd.displayPartial(self.epd.getbuffer(image))

    def _truncate_text(self, text, font, max_width):
        """Truncate text with ellipsis if it exceeds max_width pixels."""
        if not text:
            return ""
        dummy = self._create_image()
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return text
        while len(text) > 1:
            text = text[:-1]
            test = text.rstrip() + "..."
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                return test
        return text

    # ── Update logic ──────────────────────────────────────────────

    def _update_display(self, new_state, new_content):
        """Update display only if state or content changed."""
        if (new_state == self._current_state
                and new_content == self._current_content):
            # Periodic full refresh to prevent ghosting
            if (time.time() - self._last_full_refresh_time
                    >= FULL_REFRESH_INTERVAL):
                logger.info("Periodic full refresh")
                self._render_current(new_state, new_content,
                                     force_full=True)
            return

        logger.info("Display update: %s -> %s", self._current_state,
                     new_state)
        self._current_state = new_state
        self._current_content = new_content
        self._render_current(new_state, new_content)

    def _render_current(self, state, content, force_full=False):
        """Render based on current state."""
        if state == DisplayState.IDLE:
            self._render_centered_text("Scan Card")
        elif state == DisplayState.SONG_INFO:
            if force_full:
                # Temporarily render with full refresh
                image = self._create_image()
                draw = ImageDraw.Draw(image)
                title = self._truncate_text(
                    content.get('title', ''),
                    self.font_title, EPD_WIDTH - 2 * MARGIN_X
                )
                artist = self._truncate_text(
                    content.get('artist', ''),
                    self.font_artist, EPD_WIDTH - 2 * MARGIN_X
                )
                draw.text((MARGIN_X, TITLE_Y), title,
                          font=self.font_title, fill=0)
                if artist:
                    draw.text((MARGIN_X, ARTIST_Y), artist,
                              font=self.font_artist, fill=0)
                self._display_image(image, full_refresh=True)
            else:
                self._render_song_info(
                    content.get('title', ''),
                    content.get('artist', '')
                )

    # ── Main loop ─────────────────────────────────────────────────

    def run(self):
        """Main entry point."""
        self.init_display()
        self._render_centered_text("Loading...")
        self._current_state = DisplayState.INITIALIZING

        # Wait for MPD to become available
        while not self.connect_mpd():
            time.sleep(5)

        logger.info("Connected to MPD")

        while True:
            new_state, new_content = self.poll_mpd()
            self._update_display(new_state, new_content)
            time.sleep(POLL_INTERVAL)


def main():
    display = EinkDisplay()

    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down...", sig)
        display.shutdown_display()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        display.run()
    except Exception:
        logger.exception("Unexpected error")
        display.shutdown_display()
        sys.exit(1)


if __name__ == "__main__":
    main()
