# Fork Differences from Upstream

This document describes features and changes implemented in this fork (by Pavlo Shylan / crabulik) on top of the upstream [RPi-Jukebox-RFID v3](https://github.com/MiczFlor/RPi-Jukebox-RFID) project.

The fork branched from upstream at commit `8e342064` (2026-02-18) and all commits below are fork-specific unless otherwise noted.

---

## New Features

### 1. E-Ink Display Support

**Files:** `src/jukebox/components/eink_display/__init__.py`, `gpio.yaml`

A full new backend component driving a Waveshare e-ink display (EPD). Features include:

- **Now-playing screen** — shows current track title, artist, album art icon, playback state icon, progress.
- **Partial refreshes** — uses the EPD's partial-update mode to refresh only changed regions, reducing flicker and extending display life.
- **WiFi / Bluetooth status icons** — drawn inline on the status screen via pixel-art icon rendering.
- **WiFi info overlay** — after the jukebox stops playing, the display shows the device IP address (configurable delay via `show_ip_after_stop_sec`).
- **Splash screens** — startup (Dancing), shutdown (GoodBye), and sleep (Sleep) JPEG images shown at lifecycle events. Pre-rendered images live in `img/`.
- **Ukrainian locale support on display** — all display strings (track info, top charts, WiFi/IP labels) are localised via `_strings()` keyed by the jukebox language setting.
- **Unicode text rendering** — font selection supports Cyrillic and other non-ASCII characters.
- **Unknown card indicator** — when an unregistered RFID card is scanned, the display briefly shows a "unknown card" screen with the raw card ID.
- **Top-charts screen** — after the jukebox has been idle for a configurable period, the display switches to a "Top 3" chart view (last 7 or 30 days) derived from the RFID scan history.

**Config keys added to `jukebox.default.yaml`:**
```yaml
eink_display:
  show_ip_after_stop_sec: 60
  top_after_stop_sec: 120
  scan_history_file: ../../shared/settings/rfid_scan_history.jsonl
```

---

### 2. RFID Scan History Persistence

**Files:** `src/jukebox/components/rfid/reader/__init__.py`, `test/rfid/test_scan_history_persistence.py`

Every RFID scan (registered or unknown) is appended as a JSON-Lines record to a configurable file (`rfid_scan_history.jsonl`). Each record contains:

- timestamp (ISO 8601)
- reader config key
- card ID
- `is_registered` flag

Write errors are logged once and suppressed thereafter to avoid log spam. The history file is used by the e-ink top-charts feature.

**Config key added:**
```yaml
rfid:
  scan_history_file: ../../shared/settings/rfid_scan_history.jsonl
```

---

### 3. Bluetooth Device Toggle

**Files:** `src/jukebox/components/hostif/linux/__init__.py`, `src/webapp/src/components/Cards/controls/actions/host/trusted-bluetooth-device-options.js`

- Backend: new RPC-exposed functions to list trusted Bluetooth devices, connect, and disconnect them via `bluetoothctl`.
- Frontend: a new card action panel (`trusted-bluetooth-device-options.js`) lets the user pick from paired/trusted devices and toggle connection.
- Registered under `rpc_command_alias.py` so it is callable from RFID cards.

---

### 4. WiFi Toggle

**Files:** `src/jukebox/components/hostif/linux/__init__.py`

New backend functions to enable/disable WiFi via `nmcli` (NetworkManager). Exposed via RPC and usable as a card action. The e-ink display syncs its WiFi icon to the actual interface state.

---

### 5. Songs / Metadata Editor (Web App)

**Files:** `src/webapp/src/components/lists/albums/song-list/MetadataEditor.js`, `src/jukebox/components/playermpd/__init__.py`

- A new in-app metadata editor for individual tracks in the library.
- Accessible from the song list; opens a dialog to edit title, artist, album, and track number.
- Writes tags back via MPD / `eyeD3` (or equivalent) through new backend RPC commands exposed on `playermpd`.
- Card image generator integration: a "Print card" button inside the editor opens the card image generator pre-filled with the song's metadata.

---

### 6. RFID Card Image Generator (Web App)

**Files:** `src/webapp/src/components/Settings/card_print/index.js`, `src/webapp/src/components/general/CardImageGenerator.js`

A new Settings page (and reusable component) that generates a printable card image for an RFID tag:

- Displays album art, title, and artist.
- **Black-and-white mode** — toggle to produce a greyscale image suitable for monochrome printing.
- **Rotation** — 0° / 90° / 180° / 270° rotation button for landscape/portrait orientation.
- **Save as JPEG** — exports the rendered card directly to a JPEG file download.
- Accessible from the Settings menu and from the Songs editor (pre-filled per-song).

---

### 7. Ukrainian Localisation

**Files:** `src/webapp/public/locales/uk/translation.json`, `src/jukebox/components/misc.py`, `src/webapp/src/context/appsettings/`

- Full Ukrainian (`uk`) translation file for the React web app (~330 keys).
- Backend locale setting extended to recognise `uk`.
- E-ink display strings translated into Ukrainian.
- Language selector in the web app now includes Ukrainian.

---

### 8. Unknown Card Display in Web App

**Files:** `src/webapp/src/components/Player/display.js`, `src/webapp/src/config.js`

When an unregistered RFID card is scanned, the player display area in the web app shows a "Unknown card" notice with the raw card ID, making it easier to identify and register new cards.

---

### 9. Top-30 / Top-Charts on E-Ink

**Files:** `src/jukebox/components/eink_display/__init__.py`, `src/jukebox/components/playermpd/__init__.py`, `WIRING.md`, `CURRENT_SETUP.md`

Extends the scan-history feature to render a "Top 3 most-played cards" chart on the e-ink display. Two time windows are supported: last 7 days and last 30 days. The display alternates between windows after an idle timeout. Album/folder names are resolved from the card's registered folder for human-readable labels.

---

