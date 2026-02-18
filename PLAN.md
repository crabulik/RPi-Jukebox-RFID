# Implementation Plan

Step-by-step plan to adopt RPi-Jukebox-RFID to the hardware and use cases described in CURRENT_SETUP.md. Each step is independently testable on the device.

## Prerequisites

- Raspberry Pi 3 Model B V1.2 with fresh Raspberry Pi OS (Legacy) Lite 32-bit Bookworm
- SSH access to the Pi
- Waveshare 2.13" E-Ink display HAT plugged into the 40-pin header (uses its default pins)
- RC522 connected via jumper wires to SPI0 with remapped pins (see WIRING.md)
- Two illuminated buttons wired per WIRING.md (switch + LED on separate GPIO pins each)

## GPIO Wiring Plan

The E-Ink HAT is fixed to the 40-pin header and cannot be easily remapped. The RC522 uses jumper wires and is trivial to remap. Therefore: **keep E-Ink on default pins, remap RC522 around it.**

See [WIRING.md](WIRING.md) for the complete pin allocation. Summary:

### Complete Pin Map (no conflicts)

| BCM Pin | Device | Function |
|---------|--------|----------|
| GPIO6 | Stop button LED | Output — status indicator |
| GPIO7 (CE1) | RC522 | SPI chip select |
| GPIO8 (CE0) | E-Ink | SPI chip select |
| GPIO9 | RC522 | SPI MISO (E-Ink doesn't need MISO) |
| GPIO10 | Shared | SPI MOSI |
| GPIO11 | Shared | SPI SCLK |
| GPIO12 | Play/Pause button LED | Output — status + RFID flash |
| GPIO16 | Play/Pause button | Input — switch |
| GPIO17 | E-Ink | RST |
| GPIO22 | RC522 | IRQ |
| GPIO24 | E-Ink | BUSY |
| GPIO25 | E-Ink | DC |
| GPIO26 | Stop button | Input — switch |
| GPIO27 | RC522 | RST |

---

## Step 1: Base Installation

Run the project's installer on Bookworm. This handles OS packages, Python venv, MPD, PulseAudio, ZMQ, systemd service, and the web app.

```bash
cd
bash <(wget -qO- https://raw.githubusercontent.com/MiczFlor/RPi-Jukebox-RFID/future3/develop/installation/install-jukebox.sh)
```

During the interactive prompts:
- Enable static IP: **Yes**
- Disable IPv6: **Yes**
- Enable autohotspot: **No** (we'll handle Wi-Fi differently)
- Enable RFID reader: **Yes** (select RC522 in next step)
- Enable Samba: **Yes** (for uploading music files)
- Enable webapp: **Yes**
- Kiosk mode: **No**
- Disable onboard audio: **No** (we need the mini-jack)

### Test
```bash
# After reboot, check the service is running:
systemctl --user status jukebox-daemon.service

# Check logs:
tail -f ~/RPi-Jukebox-RFID/shared/logs/app.log

# Access web UI from browser:
# http://<pi-ip-address>
```

**Expected result:** Service is active, web UI loads in browser.

---

## Step 2: Configure Audio Output (Mini-Jack)

The installer sets up PulseAudio but doesn't select a specific output sink. Run the audio configuration tool to select the onboard headphone jack.

```bash
cd ~/RPi-Jukebox-RFID
./installation/components/setup_configure_audio.sh
```

This will:
1. List available PulseAudio sinks
2. Select the onboard analog output (likely `alsa_output.platform-soc_sound.stereo-fallback`)
3. Optionally enable software EQ or mono downmix (mono recommended for a single speaker)

### Test
```bash
# Copy a test audio file to the music folder:
mkdir -p ~/RPi-Jukebox-RFID/shared/audiofolders/testfolder
cp test.mp3 ~/RPi-Jukebox-RFID/shared/audiofolders/testfolder/

# Trigger playback via RPC:
cd ~/RPi-Jukebox-RFID
./tools/run_rpc_tool.sh -c player.ctrl.play

# Or from the web UI: navigate to Library, select the folder, press play
```

**Expected result:** Audio plays through the mini-jack speakers.

---

## Step 3: Configure RC522 RFID Reader (Remapped Pins)

Configure the RC522 with the remapped pin assignments from the wiring plan.

```bash
cd ~/RPi-Jukebox-RFID
source .venv/bin/activate
cd src/jukebox
python run_register_rfid_reader.py
```

Select `rc522_spi` and enter the remapped pins:
- SPI CE: **1** (GPIO7 / CE1 — moved from default CE0)
- IRQ pin: **22** (GPIO22 — moved from default GPIO24)
- RST pin: **27** (GPIO27 — moved from default GPIO25)

This writes `shared/settings/rfid.yaml` and enables SPI via `raspi-config`. **Reboot required.**

### Test
```bash
# After reboot, check RFID reader is loaded:
cd ~/RPi-Jukebox-RFID
./tools/run_rpc_tool.sh -c rfid.list_readers

# Swipe an RFID card — check logs for the card ID:
tail -f ~/RPi-Jukebox-RFID/shared/logs/app.log | grep -i rfid
```

**Expected result:** Card IDs appear in the log when cards are presented to the reader.

---

## Step 4: Register RFID Cards to Music Folders

Map each RFID card to a music folder so swiping triggers playback.

```bash
# Via the web UI: go to Library → select a folder → "Register Card"
# Then swipe the card on the reader

# Or via RPC tool:
./tools/run_rpc_tool.sh
# In the interactive prompt:
# > cards.register_card <card_id> player.ctrl.play_folder args=["testfolder"]
```

### Test
Swipe the registered card on the RC522 reader.

**Expected result:** Music from the mapped folder starts playing automatically through the speakers.

---

## Step 5: Configure Hardware Buttons and LEDs (Play/Pause + Stop)

Create `shared/settings/gpio.yaml` to map the two illuminated buttons to playback actions and status indicators.

Create the file `shared/settings/gpio.yaml`:

```yaml
pin_factory:
  type: lgpio.LGPIOFactory

output_devices:
  PlayPauseLED:
    type: LED
    connect:
      - gpio.gpioz.plugin.connectivity.register_status_led_callback
      - gpio.gpioz.plugin.connectivity.register_rfid_callback
    kwargs:
      pin: 12

  StopLED:
    type: LED
    connect:
      - gpio.gpioz.plugin.connectivity.register_status_led_callback
    kwargs:
      pin: 6

input_devices:
  PlayPause:
    type: Button
    kwargs:
      pin: 16
      pull_up: true
      bounce_time: 0.1
    actions:
      on_press:
        alias: toggle

  Stop:
    type: Button
    kwargs:
      pin: 26
      pull_up: true
      bounce_time: 0.1
    actions:
      on_press:
        package: player
        plugin: ctrl
        method: stop
```

LED behavior:
- **Play/Pause LED (GPIO12)**: OFF during boot → ON when jukebox is ready → flashes once on valid RFID swipe, three times on unknown card
- **Stop LED (GPIO6)**: OFF during boot → ON when jukebox is ready (system running indicator)

Then enable GPIO in `shared/settings/jukebox.yaml`:

```yaml
gpioz:
  enable: true
  config_file: ../../shared/settings/gpio.yaml
```

Restart the service:
```bash
systemctl --user restart jukebox-daemon.service
```

### Test
1. Restart the service — both LEDs should turn ON once startup completes
2. Start music playback (via RFID card or web UI)
3. Swipe an RFID card — Play/Pause LED should flash briefly
4. Press the play/pause button → music pauses
5. Press play/pause again → music resumes
6. Press the stop button → music stops

**Expected result:** Both buttons control playback. Both LEDs light up when jukebox is ready. Play/Pause LED flashes on RFID card detection.

---

## Step 6: Configure Idle Shutdown Timer

Edit `shared/settings/jukebox.yaml` to enable automatic shutdown after inactivity:

```yaml
timers:
  idle_shutdown:
    timeout_sec: 600    # Shut down after 10 minutes of no playback changes
```

The timer monitors MPD player status. Any playback state change (play, pause, track change) resets the countdown. Active SSH sessions also prevent shutdown.

Restart the service:
```bash
systemctl --user restart jukebox-daemon.service
```

### Test
```bash
# Check timer status via RPC:
./tools/run_rpc_tool.sh -c timers.idle_shutdown_timer.get_state

# Start playback, then stop it. Wait for the configured timeout.
# The Pi should shut down automatically.
```

**Expected result:** Pi powers off after the configured idle period. Playback activity resets the timer.

---

## Step 7: Build E-Ink Display Plugin

This is custom development — the project has no E-Ink support. Create a new plugin that subscribes to jukebox state and renders it on the Waveshare 2.13" display.

### 7a: Install Waveshare dependencies

```bash
cd ~/RPi-Jukebox-RFID
source .venv/bin/activate
pip install Pillow spidev
# If using lgpio (not RPi.GPIO), ensure the Waveshare library supports it.
# The official Waveshare library may need patching for lgpio compatibility.
```

### 7b: Create the plugin

Create `src/jukebox/components/eink_display/__init__.py`:

The plugin should:
1. Use `@plugs.initialize` to set up the display hardware on startup and show "Jukebox starting..."
2. Use `@plugs.finalize` to subscribe to the ZMQ publisher for state changes
3. Listen for player status updates (track name, playback state) and render them
4. Use `@plugs.atexit` to show "Shutting down..." on the display
5. Handle the Waveshare EPD driver for the 2.13" 250x122 display

Key events to display:
- **Boot**: "Jukebox starting..." (shown during `@plugs.initialize`)
- **Playing**: Track title, artist (from MPD metadata via player status)
- **Paused/Stopped**: Current state + last track info
- **Shutdown**: "Shutting down..." (shown during `@plugs.atexit`)

### 7c: E-Ink display configuration

The E-Ink HAT uses its default pins (no configuration needed for pin mapping). Add a config section to `shared/settings/jukebox.yaml`:

```yaml
eink_display:
  enable: true
```

### 7d: Register the plugin

Add to `shared/settings/jukebox.yaml`:

```yaml
modules:
  named:
    # ... existing entries ...
    eink: eink_display
```

Restart the service after configuration.

### Test
```bash
systemctl --user restart jukebox-daemon.service

# Watch the E-Ink display during boot — should show startup message
# Play music via RFID card — display should update with track info
# Stop music — display should show stopped state
```

**Expected result:** E-Ink display shows current jukebox state and updates on track changes.

---

## Step 8: Implement Wi-Fi Toggle via RFID Card

The project has no built-in Wi-Fi toggle. Add a custom RPC function and map an RFID card to it.

### 8a: Add Wi-Fi toggle function

Edit `src/jukebox/components/hostif/linux/__init__.py` to add:

```python
@plugin.register
def toggle_wifi():
    """Toggle WiFi radio on/off using nmcli"""
    result = subprocess.run(['nmcli', 'radio', 'wifi'], capture_output=True, text=True)
    current_state = result.stdout.strip()
    if current_state == 'enabled':
        subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', 'off'])
        return 'WiFi disabled'
    else:
        subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', 'on'])
        return 'WiFi enabled'
```

### 8b: Map an RFID card to the Wi-Fi toggle

Use the RPC tool or web UI to register a specific card:

```bash
./tools/run_rpc_tool.sh
# In the interactive prompt:
# > cards.register_card <wifi_card_id> host.toggle_wifi
```

Or edit `shared/settings/cards.yaml` directly to add the mapping.

### Test
```bash
# Verify the function works via RPC first:
./tools/run_rpc_tool.sh -c host.toggle_wifi

# Check WiFi state:
nmcli radio wifi

# Swipe the designated Wi-Fi card:
# WiFi should toggle off (Pi becomes unreachable via WiFi)
# Swipe again → WiFi comes back, SSH accessible again
```

**Expected result:** Dedicated RFID card toggles Wi-Fi on/off. When Wi-Fi is re-enabled, Pi reconnects and is SSH-accessible.

---

## Summary

| Step | What | Custom Code? | Testable Independently? |
|------|------|:------------:|:-----------------------:|
| 1 | Base installation | No | Yes |
| 2 | Audio output config | No | Yes |
| 3 | RC522 RFID setup (remapped pins) | No | Yes |
| 4 | Card-to-folder mapping | No | Yes |
| 5 | Hardware buttons + LEDs | No (config only) | Yes |
| 6 | Idle shutdown timer | No (config only) | Yes |
| 7 | E-Ink display plugin | **Yes — new plugin** | Yes |
| 8 | Wi-Fi toggle card | **Yes — new RPC function** | Yes |

Steps 1–6 use existing project functionality (configuration only).
Steps 7 and 8 require writing new code.
Pin conflicts are resolved upfront in the wiring plan (see WIRING.md).
