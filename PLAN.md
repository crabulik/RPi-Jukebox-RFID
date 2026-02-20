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

## Step 2: Configure Audio Output (Bluetooth Speaker)

The installer sets up PulseAudio but doesn't select a specific output sink. After pairing the Bluetooth speaker (Step 2b), set it as the default PulseAudio sink so MPD routes audio to it.

```bash
# List available sinks — run this after the BT speaker is connected
pactl list short sinks
```

Identify the Bluetooth sink (will look like `bluez_sink.XX_XX_XX_XX_XX_XX.a2dp_sink`), then set it as default:

```bash
# Set the BT sink as default (replace with your actual sink name)
pactl set-default-sink bluez_sink.XX_XX_XX_XX_XX_XX.a2dp_sink
```

To make this permanent across reboots, use the Jukebox audio config tool:

```bash
cd ~/RPi-Jukebox-RFID
./installation/components/setup_configure_audio.sh
```

Select the Bluetooth sink from the list when prompted.

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

**Expected result:** Audio plays through the Bluetooth speaker.

---

## Step 2b: Configure Bluetooth Audio Auto-Connect

If using a Bluetooth speaker, it will not automatically reconnect after reboot by default. The `br-connection-profile-unavailable` error occurs because the system-level bluetooth service starts before PulseAudio has registered its A2DP audio profiles.

### Pair and trust the device (once)

```bash
bluetoothctl
scan on
# wait for your device MAC to appear, then:
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
exit
```

### Create a boot auto-connect service

```bash
sudo nano /etc/systemd/system/bt-autoconnect.service
```

```ini
[Unit]
Description=Bluetooth auto-connect
After=bluetooth.service pulseaudio.service
Requires=bluetooth.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for i in $(seq 1 10); do sleep 3; bluetoothctl connect XX:XX:XX:XX:XX:XX && break; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Replace `XX:XX:XX:XX:XX:XX` with your speaker's MAC address.

```bash
sudo systemctl daemon-reload
sudo systemctl enable bt-autoconnect.service
```

The service retries every 3 seconds up to 10 times (30s total), stopping as soon as the connection succeeds. The delay is necessary because PulseAudio registers A2DP profiles after the bluetooth service is up.

### Test

```bash
sudo reboot

# After reboot:
systemctl status bt-autoconnect.service
# Should show: active (exited) with no errors

bluetoothctl info XX:XX:XX:XX:XX:XX
# Should show: Connected: yes
```

**Expected result:** Bluetooth speaker connects automatically within ~10 seconds of boot with no manual intervention.

---

## Step 2c: RFID-Based Bluetooth Device Switching

This setup allows assigning a card action that disconnects the currently connected Bluetooth audio device and connects a specific trusted device selected for that card.

### Runtime flow (after implementation)

1. RFID card is scanned
2. Card alias `connect_trusted_bluetooth_device` is resolved by the card database
3. Host plugin validates target address is in trusted devices
4. Any currently connected Bluetooth device(s) are disconnected
5. Selected trusted device is connected via `bluetoothctl connect <MAC>`
6. Connectivity state updates are published on `host.connectivity`

### Register a new Bluetooth device so it appears in Web UI

Run once per device:

```bash
bluetoothctl
scan on
# wait for your device MAC, then:
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
exit
```

Verify the device is trusted:

```bash
bluetoothctl info XX:XX:XX:XX:XX:XX
# Expect: Trusted: yes
```

Optional RPC verification from Jukebox:

```bash
cd ~/RPi-Jukebox-RFID
./tools/run_rpc_tool.sh -c host.get_trusted_bluetooth_devices
```

### Register an RFID card for a specific trusted device

1. Open Web UI → **Cards** → **Register card**
2. Swipe card to capture card ID
3. Select action **System**
4. Select command **Connect trusted Bluetooth device**
5. Select target device from dropdown (trusted devices only)
6. Save

### Test

1. Connect device A manually
2. Swipe card registered to device B
3. Check:

```bash
bluetoothctl info XX:XX:XX:XX:XX:XX
# Device B should show: Connected: yes
```

**Expected result:** current Bluetooth connection is switched to the trusted device assigned to the card.

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
    type: ShortLongPressButton
    kwargs:
      pin: 16
      pull_up: true
      bounce_time: 0.1
      hold_time: 2.0
    actions:
      on_short_press:
        alias: toggle
      on_long_press:
        package: player
        plugin: ctrl
        method: replay_if_stopped

  Stop:
    type: ShortLongPressButton
    kwargs:
      pin: 26
      pull_up: true
      bounce_time: 0.1
      hold_time: 3.0
    actions:
      on_short_press:
        package: player
        plugin: ctrl
        method: stop
      on_long_press:
        package: host
        plugin: play_random_folder
```

> **Note:** `play_random_folder` is a custom RPC function added in Step 8b.
> `on_short_press` fires on button **release**; `on_long_press` fires immediately after holding 1 second.

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
4. Short press Play/Pause → music pauses
5. Short press Play/Pause again → music resumes
6. Short press Stop → music stops
7. Short press Play/Pause after stop → nothing happens (toggle does not restart after stop)
8. Long press Play/Pause (1s) after stop → last folder restarts from beginning
9. Long press Stop (1s) → random folder starts playing

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

## Step 8: Custom RPC Functions in hostif

Two custom functions are added to `src/jukebox/components/hostif/linux/__init__.py`.

### 8a: play_random_folder (already implemented)

Picks a random folder from the MPD library and plays it. Used by the Stop button long press (Step 5).

```python
@plugin.register
def play_random_folder():
    """Pick a random folder from the music library and start playing it"""
    all_entries = plugin.call('player', 'ctrl', 'list_all_dirs')
    if not all_entries:
        logger.warning('play_random_folder: no entries found in library')
        return
    folders = [entry['directory'] for entry in all_entries if 'directory' in entry]
    if not folders:
        logger.warning('play_random_folder: no folders found in library')
        return
    folder = random.choice(folders)
    logger.info(f'play_random_folder: selected folder "{folder}"')
    plugin.call('player', 'ctrl', 'play_folder', args=[folder])
```

Also requires `import random` at the top of the file.

Called via gpio.yaml as:
```yaml
package: host
plugin: play_random_folder
```

### 8b: Add Wi-Fi toggle function

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

### 8c: Map an RFID card to the Wi-Fi toggle

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

## Step 9: Status Bar — Wi-Fi and Bluetooth Icons

Add a persistent status bar in the top-right corner of the web app showing connectivity icons. An icon is shown only when the corresponding interface is active; it disappears otherwise.

- **Wi-Fi icon**: visible when Wi-Fi radio is enabled (`nmcli radio wifi` = `enabled`)
- **Bluetooth icon**: visible when at least one Bluetooth device is connected (`bluetoothctl info` returns `Connected: yes`)

### 9a: Backend — publish connectivity state

Add a periodic publisher to `src/jukebox/components/hostif/linux/__init__.py` that emits a `host.connectivity` ZMQ topic on a timer (every 10 seconds), following the existing `publish_cpu_temperature` / `GenericEndlessTimerClass` pattern.

```python
@plugin.register
def get_connectivity_status():
    """Return Wi-Fi and Bluetooth connectivity state as a dict."""
    # Wi-Fi: nmcli radio wifi → 'enabled' or 'disabled'
    wifi_ret = subprocess.run(
        ['nmcli', 'radio', 'wifi'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        check=False, stdin=subprocess.DEVNULL,
    )
    wifi_on = wifi_ret.returncode == 0 and wifi_ret.stdout.decode().strip() == 'enabled'

    # Bluetooth: bluetoothctl info → contains 'Connected: yes' if any device connected
    bt_ret = subprocess.run(
        ['bluetoothctl', 'info'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        check=False, stdin=subprocess.DEVNULL,
    )
    bt_connected = bt_ret.returncode == 0 and 'Connected: yes' in bt_ret.stdout.decode()

    return {'wifi': wifi_on, 'bluetooth': bt_connected}


@plugin.register
def publish_connectivity_status():
    status = get_connectivity_status()
    jukebox.publishing.get_publisher().send('host.connectivity', status)
```

Wire `publish_connectivity_status` into `finalize()` as a `GenericEndlessTimerClass` (interval: 10 s), following the exact same pattern as `timer_temperature`. Register and cancel it in `atexit()` too.

### 9b: Frontend — connectivity context

Create `src/webapp/src/context/connectivity/index.js` — a React context that subscribes to the `host.connectivity` ZMQ PubSub topic using the existing `PubSubProvider`/socket pattern and exposes `{ wifi, bluetooth }` booleans. Default both to `false` until first message arrives.

Wrap `<ConnectivityProvider>` in `App.js` alongside the existing providers.

### 9c: Frontend — StatusBar component

Create `src/webapp/src/components/StatusBar/index.js`:

- Fixed position top-right, `zIndex` above content (≥ 1200)
- Uses `WifiIcon` and `BluetoothIcon` from `@mui/icons-material`
- Renders each icon **only** when the corresponding boolean is `true`
- Small, muted icons (`fontSize="small"`, `color="action"`) so they don't compete with content

```jsx
import WifiIcon from '@mui/icons-material/Wifi';
import BluetoothIcon from '@mui/icons-material/Bluetooth';
import Box from '@mui/material/Box';
import { useContext } from 'react';
import ConnectivityContext from '../../context/connectivity';

const StatusBar = () => {
  const { wifi, bluetooth } = useContext(ConnectivityContext);
  return (
    <Box sx={{ position: 'fixed', top: 8, right: 12, display: 'flex', gap: 0.5, zIndex: 1200 }}>
      {wifi && <WifiIcon fontSize="small" color="action" />}
      {bluetooth && <BluetoothIcon fontSize="small" color="action" />}
    </Box>
  );
};
```

Mount `<StatusBar />` once in `router.js` outside the `<Routes>` block, alongside `<Navigation />`.

### Test

```bash
# Verify backend publishes:
./tools/run_publicity_sniffer.sh
# Should see 'host.connectivity' messages every ~10 s

# Verify via RPC:
./tools/run_rpc_tool.sh -c host.get_connectivity_status
# → {"wifi": true, "bluetooth": true}  (or false depending on state)

# UI checks:
# 1. Open web app — icons appear top-right matching current state
# 2. Toggle Wi-Fi off (RPC or RFID card) — Wi-Fi icon disappears within 10 s
# 3. Disconnect Bluetooth speaker — Bluetooth icon disappears within 10 s
```

**Expected result:** Top-right corner shows Wi-Fi and/or Bluetooth icons reflecting live connectivity state. Icons disappear when the interface is inactive.

---

## Summary

| Step | What | Custom Code? | Testable Independently? |
|------|------|:------------:|:-----------------------:|
| 1 | Base installation | No | Yes |
| 2 | Audio output (Bluetooth speaker) | No | Yes |
| 2b | Bluetooth audio auto-connect on boot | No (config only) | Yes |
| 3 | RC522 RFID setup (remapped pins) | No | Yes |
| 4 | Card-to-folder mapping | No | Yes |
| 5 | Hardware buttons + LEDs | No (config only) | Yes |
| 6 | Idle shutdown timer | No (config only) | Yes |
| 7 | E-Ink display plugin | **Yes — new plugin** | Yes |
| 8a | play_random_folder (Stop long press) | **Yes — new RPC function** | Yes |
| 8b | Wi-Fi toggle card | **Yes — new RPC function** | Yes |
| 9 | Status bar (Wi-Fi + BT icons) | **Yes — backend + frontend** | Yes |

Steps 1–6 use existing project functionality (configuration only).
Steps 7, 8, and 9 require writing new code.
Pin conflicts are resolved upfront in the wiring plan (see WIRING.md).
