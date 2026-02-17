# Waveshare 2.13" e-Paper HAT Display

Shows the current Phoniebox state on a Waveshare 2.13 inch e-Paper HAT (V4).

## Display States

- **Loading...** — shown during service startup while waiting for MPD
- **Scan Card** — idle, ready for an RFID card
- **Song title + artist** — shown when a track is selected or playing

The display only refreshes when content changes. A full refresh runs every 30 minutes to prevent ghosting.

## Hardware

- [Waveshare 2.13inch e-Paper HAT (V4)](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT)
- 250x122 pixels, SPI interface
- Plugs directly onto the Raspberry Pi GPIO header

## Prerequisites

- SPI must be enabled (`sudo raspi-config` > Interface Options > SPI)
- Python 3.9+
- Phoniebox installed and running (MPD on localhost:6600)

## Files

| File | Description |
|------|-------------|
| `eink_display.py` | Main display daemon |
| `eink-display.service.default.sample` | systemd service template |
| `requirements.txt` | Python dependencies |
| `install.sh` | Installation script |

## Installation

```bash
cd /home/pi/RPi-Jukebox-RFID/components/displays/e-ink-waveshare-2in13
sudo bash install.sh
```

The install script enables SPI (if needed), installs Python dependencies, and sets up the systemd service.

## Manual Service Control

```bash
# Check status
sudo systemctl status phoniebox-eink-display

# View logs
journalctl -u phoniebox-eink-display -f

# Stop / start / restart
sudo systemctl stop phoniebox-eink-display
sudo systemctl start phoniebox-eink-display
sudo systemctl restart phoniebox-eink-display
```

## Older HAT Revisions

This code targets the V4 hardware revision (current shipping version). For older revisions, change the import in `eink_display.py`:

```python
# V4 (default)
from waveshare_epd import epd2in13_V4

# V3
from waveshare_epd import epd2in13_V3

# V2
from waveshare_epd import epd2in13_V2
```

## Troubleshooting

- **Display not responding** — Verify SPI is enabled: `ls /dev/spidev*` should show device files. Reboot after enabling SPI.
- **Permission errors** — The `pi` user must be in the `spi` and `gpio` groups (default on Raspberry Pi OS).
- **SPI conflict with RFID reader** — The e-Paper HAT uses SPI0 CE0. SPI-based RFID readers (RC522) typically use SPI0 CE1, so they coexist. If both use the same chip-select, only one can be active at a time.
