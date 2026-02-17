#!/usr/bin/env bash

if [[ $(id -u) != 0 ]]; then
    echo "This script should be run using sudo"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="phoniebox-eink-display"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== Phoniebox E-Ink Display Installation ==="

# Enable SPI if not already enabled
SPI_ENABLED=false
for cfg in /boot/config.txt /boot/firmware/config.txt; do
    if [[ -f "$cfg" ]] && grep -q "^dtparam=spi=on" "$cfg"; then
        SPI_ENABLED=true
        break
    fi
done

if [[ "$SPI_ENABLED" = false ]]; then
    echo "Enabling SPI interface..."
    raspi-config nonint do_spi 0
    echo "SPI enabled. A reboot may be required."
fi

echo "Installing Python dependencies..."
python3 -m pip install --upgrade --force-reinstall -q -r "${SCRIPT_DIR}/requirements.txt"

if [[ -f "$SERVICE_FILE" ]]; then
    echo "${SERVICE_FILE} already exists."
    systemctl daemon-reload
    echo "Restarting service..."
    systemctl restart "${SERVICE_NAME}.service"
else
    echo "Installing service file..."
    cp "${SCRIPT_DIR}/eink-display.service.default.sample" "$SERVICE_FILE"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service"
    systemctl start "${SERVICE_NAME}.service"
fi

SERVICE_STATUS="$(systemctl is-active "${SERVICE_NAME}.service")"
if [[ "${SERVICE_STATUS}" = "active" ]]; then
    echo "E-Ink Display Service started successfully."
else
    echo "ERROR: Service not running. Check with:"
    echo "  journalctl -u ${SERVICE_NAME}.service -f"
    exit 1
fi
