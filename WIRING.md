# Wiring Guide

Pin wiring for Raspberry Pi 3 Model B V1.2 with Waveshare 2.13" E-Ink HAT, RC522 RFID reader, two illuminated hardware buttons.

Strategy: The E-Ink HAT plugs directly onto the 40-pin header and keeps its default pins. The RC522 is connected via jumper wires with remapped pins to avoid conflicts.

## Raspberry Pi 3 GPIO Header

```
                    +-----+
           3.3V  1 | o o | 2  5V
  (SDA1) GPIO2  3 | o o | 4  5V
  (SCL1) GPIO3  5 | o o | 6  GND
          GPIO4  7 | o o | 8  GPIO14 (TXD)
            GND  9 | o o | 10 GPIO15 (RXD)
         GPIO17 11 | o o | 12 GPIO18
  -----> GPIO27 13 | o o | 14 GND
  -----> GPIO22 15 | o o | 16 GPIO23
           3.3V 17 | o o | 18 GPIO24 <-----
 (MOSI) GPIO10  19 | o o | 20 GND
 (MISO)  GPIO9  21 | o o | 22 GPIO25 <-----
 (SCLK) GPIO11  23 | o o | 24 GPIO8  (CE0) <-----
            GND 25 | o o | 26 GPIO7  (CE1) <-----
          GPIO0 27 | o o | 28 GPIO1
          GPIO5 29 | o o | 30 GND
  -----> GPIO6  31 | o o | 32 GPIO12 <-----
         GPIO13 33 | o o | 34 GND
         GPIO19 35 | o o | 36 GPIO16 <-----
  -----> GPIO26 37 | o o | 38 GPIO20
            GND 39 | o o | 40 GPIO21
                    +-----+

  <----- = used pin (active device connected)
```

## E-Ink Display (Waveshare 2.13" HAT)

Plugs directly onto the 40-pin header. No rewiring needed.

```
E-Ink HAT Pin    BCM GPIO    Physical Pin    RPi Function
───────────────────────────────────────────────────────────
VCC              —           1               3.3V
GND              —           6               GND
DIN (MOSI)       GPIO10      19              SPI0 MOSI
CLK (SCLK)       GPIO11      23              SPI0 SCLK
CS               GPIO8       24              SPI0 CE0
DC               GPIO25      22              Data/Command
RST              GPIO17      11              Reset
BUSY             GPIO24      18              Busy signal
```

## RC522 RFID Reader

Connected via jumper wires. Pins remapped to avoid E-Ink conflicts.

```
RC522 Pin     BCM GPIO    Physical Pin    Notes
──────────────────────────────────────────────────────────
3.3V          —           17              3.3V (pin 1 also works)
GND           —           20              GND (any GND pin works)
MOSI          GPIO10      19              Shared with E-Ink
MISO          GPIO9       21              RC522 only (E-Ink has no MISO)
SCK           GPIO11      23              Shared with E-Ink
SDA (CS)      GPIO7       26              SPI0 CE1 (default was CE0/GPIO8)
IRQ           GPIO22      15              Interrupt (default was GPIO24)
RST           GPIO27      13              Reset (default was GPIO25)
```

### RC522 Software Configuration

When running `run_register_rfid_reader.py`, enter these values:

| Parameter | Value |
|-----------|-------|
| Reader | `rc522_spi` |
| SPI CE | `1` |
| IRQ pin | `22` |
| RST pin | `27` |

## Hardware Buttons (Illuminated)

Each button has two independent circuits: a normally-open switch and a built-in LED. The switch connects to a GPIO input (with internal pull-up). The LED connects to a separate GPIO output for software control.

### Button Switch Wiring

```
Button          BCM GPIO    Physical Pin    Nearby GND
────────────────────────────────────────────────────────
Play/Pause      GPIO16      36              39
Stop            GPIO26      37              39
```

Wiring per button switch:
```
GPIO pin ────── Switch ────── GND
         (normally open)
```

No external resistors needed — `pull_up: true` in `gpio.yaml` enables the internal pull-up.

### Button LED Wiring

```
Button LED       BCM GPIO    Physical Pin    Notes
─────────────────────────────────────────────────────────
Play/Pause LED   GPIO12      32              Software-controlled
Stop LED         GPIO6       31              Software-controlled
```

Wiring per button LED (assuming LED has built-in current-limiting resistor):
```
GPIO pin ────── LED(+) ────── LED(-) ────── GND
```

If the button LED does NOT have a built-in resistor, add a 220-330 ohm resistor in series between the GPIO pin and LED anode.

### Button LED Behavior

| LED | Behavior |
|-----|----------|
| Play/Pause LED | OFF during boot. ON when jukebox is ready. Flashes once on valid RFID swipe, three times on unknown card. |
| Stop LED | OFF during boot. ON when jukebox is ready (acts as "system running" indicator). |

## Safe Shutdown Button

A single momentary push button (normally open, no latch) that:
- **Shuts down** the OS cleanly when the system is running
- **Restarts** the board when halted-but-still-powered (hardware feature of GPIO 3 / BCM SCL1)

> Note: restart via the button only works when power is still connected after a software shutdown.
> It does **not** replace a physical power cycle.

### Wiring

```
Button pin 1 ────── Physical Pin 5  (BCM GPIO 3 / SCL1)
Button pin 2 ────── Physical Pin 9  (GND)
```

No external resistor needed — GPIO 3 has an internal pull-up.

```
Physical Pin    BCM GPIO    Function
────────────────────────────────────
5               GPIO3       Shutdown signal input
9               GND         Button ground
```

### OS Configuration

**Step 1 — Open the boot config:**

```bash
sudo nano /boot/firmware/config.txt
```

> For Raspberry Pi OS older than Bookworm the path is `/boot/config.txt`.

**Step 2 — Add the overlay under the `[all]` / Jukebox Boot Config section:**

The `[all]` section is at the bottom of the file. Add the line after `disable_splash=1`:

```
[all]

## Jukebox Boot Config
disable_splash=1
dtoverlay=gpio-shutdown
```

The `gpio-shutdown` overlay defaults to GPIO 3 (BCM), which matches our wiring.
No additional parameters are needed.

**Step 3 — Save and reboot:**

```bash
# In nano: Ctrl+O  →  Enter  →  Ctrl+X
sudo reboot
```

**Step 4 — Verify:**

After reboot, press the button once. The system should cleanly shut down (`sudo poweroff` equivalent).
Once halted, press the button again — the board restarts.

## Complete Pin Allocation

```
Physical                                              Physical
Pin      Function          BCM         Function       Pin
─────────────────────────────────────────────────────────────
 1       3.3V [E-Ink]      —           5V              2
 3       (free)            GPIO2       5V              4
 5       Shutdown btn      GPIO3       GND             6  [E-Ink]
 7       (free)            GPIO4       GPIO14          8
 9       GND [shutdown]    —           GPIO15         10
11       E-Ink RST         GPIO17      GPIO18         12
13       RC522 RST         GPIO27      GND            14
15       RC522 IRQ         GPIO22      GPIO23         16
17       3.3V [RC522]      —           GPIO24         18  E-Ink BUSY
19       SPI MOSI [shared] GPIO10      GND            20  [RC522]
21       SPI MISO [RC522]  GPIO9       GPIO25         22  E-Ink DC
23       SPI SCLK [shared] GPIO11      GPIO8          24  E-Ink CS (CE0)
25       (free)            —           GPIO7          26  RC522 CS (CE1)
27       (free)            GPIO0       GPIO1          28
29       (free)            GPIO5       GND            30
31       Stop LED          GPIO6       GPIO12         32  Play/Pause LED
33       (free)            GPIO13      GND            34
35       (free)            GPIO19      GPIO16         36  Play/Pause btn
37       Stop btn          GPIO26      GPIO20         38
39       GND [buttons]     —           GPIO21         40
─────────────────────────────────────────────────────────────

Used: 15 GPIO pins (+ 4 power/ground)
Free: 15 GPIO pins remaining
```
