# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Phoniebox / RPi Jukebox RFID Version 3** — an RFID-controlled music jukebox for Raspberry Pi. The core is a Python daemon with a plugin architecture, communicating with a React web app via ZMQ (RPC + PubSub over WebSocket).

Current version: 3.6.0-alpha. Minimum Python: 3.9. CI tests Python 3.9–3.13.

## Common Commands

### Linting & Testing

```bash
./run_flake8.sh                    # Lint all Python files
./run_flake8.sh path/to/file.py    # Lint specific file

./run_pytest.sh                    # Run all tests
./run_pytest.sh test/cfghandler/test_cfghandler.py           # Single test file
./run_pytest.sh -k test_ordereddict_getn                     # Single test by name
./run_pytest.sh --cov --cov-report xml --cov-config=.coveragerc  # With coverage
```

### Running the Jukebox

```bash
./run_jukebox.sh          # Start (handles venv, cd, etc.)
./run_jukebox.sh -vv      # Debug logging
```

### Web App (src/webapp/)

```bash
cd src/webapp
./run_rebuild.sh -u       # First build (install deps + build)
./run_rebuild.sh          # Rebuild only
npm start                 # Dev server at localhost:3000
npm test                  # Run webapp tests
```

### Docker Dev Environment

```bash
docker build -f docker/Dockerfile.libzmq -t libzmq:local .
# Mac:
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.mac.yml up
# Linux:
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.linux.yml up
```

### Developer Tools

```bash
./tools/run_rpc_tool.sh                  # Interactive RPC CLI to running jukebox
./tools/run_rpc_tool.sh -c host.shutdown # Single RPC command
./tools/run_publicity_sniffer.sh         # Monitor ZMQ publish messages
./run_docgeneration.sh                   # Generate API docs from docstrings
./run_markdownlint.sh                    # Lint markdown files
```

## Architecture

### Communication Pattern

```
Web App (React) ←→ ZMQ WebSocket (ports 5556/5557) ←→ Jukebox Core (Python)
                                                        ↕
                                                    MPD (music playback)
```

- **RPC** (port 5555 TCP / 5556 WS): Web App → Jukebox commands
- **PubSub** (port 5558 TCP / 5557 WS): Jukebox → Web App state updates

### Plugin System (`src/jukebox/jukebox/plugs.py`)

The core is built around dynamic plugin loading. Components register callables via `@plugs.register` decorator. The RPC server exposes registered callables to clients. Plugins are loaded at startup based on `jukebox.yaml` config (`modules.named` and `modules.others` sections).

### Key Source Layout

- `src/jukebox/run_jukebox.py` — main entry point → `jukebox/daemon.py` (JukeBox class)
- `src/jukebox/jukebox/` — core library: plugs, cfghandler, rpc/, publishing/
- `src/jukebox/components/` — plugin packages: playermpd, volume, rfid, gpio, controls, timers, mqtt, etc.
- `src/jukebox/components/rfid/hardware/` — RFID reader drivers (rc522, pn532, rdm6300, generic_usb, generic_nfcpy, fake_reader_gui)
- `src/webapp/` — React 17 SPA (Material UI, i18next, jszmq)
- `resources/default-settings/` — template config files (copied to `shared/settings/` at install)
- `shared/settings/` — runtime YAML config (created during installation, not in repo)
- `test/` — pytest tests

### Config Handling

YAML configs use `ruamel.yaml` (not PyYAML) via thread-safe `cfghandler.py`. All config paths are relative from `src/jukebox/` (using `../../`).

## Code Conventions

### Python

- PEP 8 enforced via flake8: max line length 127, max complexity 12
- 4-space indentation, LF line endings, UTF-8
- Docstrings required for modules and public functions
- `__init__.py` files may have unused imports (F401 ignored)
- `scratch*` directories are gitignored and flake8-excluded — use for local experiments

### JavaScript / Web App

- React 17, Node 20.x, 2-space indent
- ESLint with react-app config

### File/Folder Naming

- All lowercase, words separated by underscores (not dashes — dashes break Python imports)
- Descriptive, general-to-specific (e.g., `battery_monitor`, not `monitor_battery`)

## Branch & PR Workflow

- Main development branch: `future3/develop` (aliased as `develop`)
- PRs target `future3/develop`
- Run `./run_flake8.sh` and `./run_pytest.sh` before every PR
- Commit message prefixes for trivial changes: `(docs)`, `(maint)`, `(packaging)`
