# Current Setup

This document contains information regarding the current hardware setup of the project and the main usecases.

## Hardware Setup

- Raspberry Pi 3 Model B V1.2
  - OS: Raspberry Pi OS (Legacy) Lite, 32-bit, Debian version 12 (bookworm), Kernel version 6.12
- SD Card 16GB
- Audio will be taken from the Miniu Jack output of the Raspberry Pi 3
- RFID Reader (RC522)
- Speakers connected via mini-Jack to Mini-Jack cable to the Raspberry Pi 3
- EInk Display: Waveshare 250x122, 2.13inch E-Ink display HAT for Raspberry Pi
- Two Hardware buttons for play/pause and stop functions. Each button has a light indicator.
- Safe shutdown button (momentary, Pin 5 / GPIO 3 + Pin 9 / GND)

## Main Use Cases

- Select a song by RFID cards codes located on the SD Card
- The song starts playing automatically after the card is detected
- Display current track on EInk display
- Control playback with hardware buttons (play/pause, stop)
- A special RFID card is used to turn on and off the WiFi
- When the WiFi is turned on, the jukebox should connect to the network and be accessible via SSH
- When the Jukebox is booting, the EInk display should show the current status of the jukebox
- The jukebox should automatically turn off after a certain period of inactivity
