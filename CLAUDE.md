# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phoniebox (RPi-Jukebox-RFID) is a contactless jukebox for Raspberry Pi that plays audio files, playlists, podcasts, web streams, and Spotify content triggered by RFID cards. This is the **Version 2.x** codebase on the `develop` branch.

## Languages and Architecture

This is a polyglot project:

- **Bash/Shell** — Core playout control (`scripts/playout_controls.sh`), RFID trigger logic (`scripts/rfid_trigger_play.sh`), and installation scripts (`scripts/installscripts/`)
- **PHP** — Web application in `htdocs/` (jQuery frontend, REST-like API in `htdocs/api/`)
- **Python** — RFID reader daemons (`scripts/daemon_rfid_reader.py`, `scripts/Reader.py`), GPIO control module (`components/gpio_control/`), and hardware component integrations under `components/`

Audio playback is handled by **MPD** (Music Player Daemon). The `components/` directory contains modular hardware/software integrations (GPIO buttons, RFID readers, displays, Bluetooth, MQTT).

## Commands

### Python tests and linting
```bash
# Run all Python tests with coverage
pytest --cov --cov-config=.coveragerc --cov-report xml

# Run a single Python test file
pytest components/gpio_control/test/test_gpio_control.py

# Python linting
flake8 --config .flake8
```

### PHP tests
```bash
# Run PHP tests (excludes real-env group)
composer run-script test

# Run all PHP tests including real-env
composer run-script test-all
```

### Markdown linting
```bash
markdownlint-cli2 --config .markdownlint-cli2.yaml
```

### Docker (CI testing)
```bash
docker build -t rpi-jukebox-rfid:debian-latest -f ci/Dockerfile.debian --platform=linux/arm/v7 --target=code .
```

## Key Conventions

- **Branch model**: Development happens on `develop`. PRs target `develop`, not `master`.
- **File/folder naming**: All lowercase, words separated by dashes (not underscores or camelCase).
- **GPIO**: Must use `RPi.GPIO` API via the `rpi-lgpio` shim package. **Never** install the original `RPi.GPIO` directly — it breaks GPIO on kernel 6.6+ (bookworm). See `requirements-excluded.txt`.
- **Python style**: flake8 with max line length 127, max complexity 12. Config in `.flake8`.
- **Indentation**: 4 spaces default, 2 spaces for JS/YAML. See `.editorconfig`.
- **Python tests** mock `RPi.GPIO` via `conftest.py` in `components/gpio_control/test/` so tests run on non-Pi hardware.
- Code must work on all Raspberry Pi models under both stable and legacy Raspberry Pi OS versions.
