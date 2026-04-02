# How to Install — Orest3 Setup

Step-by-step guide to reproduce the exact hardware and software setup described in [CURRENT_SETUP.md](../../CURRENT_SETUP.md) and [WIRING.md](WIRING.md).

For deeper explanations of any step see [documentation/builders/installation.md](../builders/installation.md).

---

## 1. Flash Raspberry Pi OS

1. Download and run [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Device: **Raspberry Pi 3**.
3. OS: **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (Legacy, 32-bit)** — Bookworm.
4. Storage: your 16 GB SD card.
5. In **Edit Settings** before writing:
   - Set hostname (e.g. `jukebox`), username, password.
   - Configure Wi-Fi SSID + password.
   - **Services** tab → enable SSH with password authentication.
6. Flash and insert the card.

---

## 2. First Boot & SSH

```bash
ssh <user>@jukebox.local
```

If `.local` does not resolve, find the IP from your router.

---

## 3. Install Jukebox Software (fork)

Run the one-liner from the fork:

```bash
cd; bash <(wget -qO- https://raw.githubusercontent.com/crabulik/RPi-Jukebox-RFID/orest3/installation/install-jukebox.sh)
```

This installs from the `orest3` branch of `crabulik/RPi-Jukebox-RFID`.

> Installation takes 20–60 minutes. To watch the log in a second terminal:
> ```bash
> tail -f ~/INSTALL-*.log
> ```

After it finishes, the service starts automatically.

---

## 4. Install E-Ink Display Dependencies

The Waveshare e-ink component requires extra packages not installed by the main script:

```bash
# System font for Cyrillic support
sudo apt install -y fonts-freefont-ttf

# Python driver for Waveshare 2.13" EPD (V4)
source ~/RPi-Jukebox-RFID/.venv/bin/activate
pip install waveshare-epaper Pillow
deactivate
```

---

## 5. Enable SPI

Required for the e-ink display and RC522 RFID reader.

```bash
sudo raspi-config
# Interface Options → SPI → Enable
sudo reboot
```

---

## 6. Wire the Hardware

Follow [WIRING.md](WIRING.md) for the full pin diagram. Summary:

| Device | Key pins (BCM) |
|--------|---------------|
| E-Ink HAT | plugs onto 40-pin header directly — no jumpers needed |
| RC522 RFID | MOSI/MISO/SCLK shared; CS→GPIO7, IRQ→GPIO22, RST→GPIO27 |
| Play/Pause button | switch→GPIO16, LED→GPIO12 |
| Stop button | switch→GPIO26, LED→GPIO6 |
| Shutdown button | GPIO3 (pin 5) + GND (pin 9) |

---

## 7. Register the RFID Reader

```bash
cd ~/RPi-Jukebox-RFID
source .venv/bin/activate
python3 src/jukebox/run_register_rfid_reader.py
```

Enter these values when prompted:

| Prompt | Value |
|--------|-------|
| Reader type | `rc522_spi` |
| SPI CE | `1` |
| IRQ GPIO pin | `22` |
| Reset GPIO pin | `27` |

This writes `shared/settings/rfid.yaml`.

---

## 8. Configure `jukebox.yaml`

```bash
systemctl --user stop jukebox-daemon
nano ~/RPi-Jukebox-RFID/shared/settings/jukebox.yaml
```

Key settings to check/change:

```yaml
# Enable GPIO (buttons + LEDs)
gpioz:
  enable: true
  config_file: ../../shared/settings/gpio.yaml

# Enable e-ink display
eink_display:
  enable: true
  locale: uk          # or 'en'
  show_ip_after_stop_sec: 60

# RFID scan history (used by top-charts on display)
rfid:
  scan_history_file: ../../shared/settings/rfid_scan_history.jsonl

# Idle auto-shutdown (seconds; 0 = disabled)
timers:
  idle_shutdown:
    timeout_sec: 3600

# Web app language
webapp:
  default_language: uk   # or 'en', 'de'
```

---

## 9. Configure GPIO (`gpio.yaml`)

Copy the repo's pre-configured file:

```bash
cp ~/RPi-Jukebox-RFID/gpio.yaml ~/RPi-Jukebox-RFID/shared/settings/gpio.yaml
```

This sets up Play/Pause (GPIO16 + LED GPIO12) and Stop (GPIO26 + LED GPIO6) buttons.

---

## 10. Configure Safe Shutdown Button

Add the `gpio-shutdown` overlay to boot config:

```bash
sudo nano /boot/firmware/config.txt
```

Under the `[all]` section add:

```
dtoverlay=gpio-shutdown
```

Save and reboot. After reboot, pressing the button on GPIO3 will cleanly shut down the OS.

---

## 11. Start and Verify

```bash
systemctl --user start jukebox-daemon
systemctl --user status jukebox-daemon
```

Check the web app at `http://jukebox.local` (or the device IP).

To test the e-ink display and debug jukebox output:

```bash
cd ~/RPi-Jukebox-RFID
./run_jukebox.sh -vv
```

---

## 12. Add Music

Place audio files (MP3, FLAC, etc.) into:

```
~/RPi-Jukebox-RFID/shared/audiofolders/
```

Folder structure: one subfolder per album/playlist. The web app's library view refreshes automatically.

---

## 13. Register RFID Cards

Use the web app → **Cards** section, or scan a card — an "unknown card" notice appears in the player display with the raw card ID. Then assign it to a folder/action from the **Cards** editor.

---

## References

| Doc | Purpose |
|-----|---------|
| [WIRING.md](WIRING.md) | Full GPIO pin diagram |
| [CURRENT_SETUP.md](../../CURRENT_SETUP.md) | Hardware inventory |
| [diff-to-original.md](diff-to-original.md) | Fork-specific features overview |
| [documentation/builders/installation.md](../builders/installation.md) | Upstream full install guide |
| [documentation/builders/configuration.md](../builders/configuration.md) | Config file reference |
| [documentation/builders/gpio.md](../builders/gpio.md) | GPIO YAML reference |
