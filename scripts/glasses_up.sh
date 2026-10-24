#!/usr/bin/env bash
# Put the glasses client on the Pi and drive the real SSD1306.
#   scripts/glasses_up.sh selftest            copy + install + fake cues on the OLED (no network to the Mac needed)
#   scripts/glasses_up.sh live [MAC_IP]       follow this Mac's receiver (start it with --host MAC_IP first)
# Env: PI=pi@glasses-pi.local  FLIP="--flip-x" (if the combiner mirrors the image)
set -euo pipefail
cd "$(dirname "$0")/.."
PI="${PI:-pi@glasses-pi.local}"
MODE="${1:-selftest}"
ssh_pi() { ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$PI" "$@"; }

echo "== Checking $PI"
ssh_pi 'echo "$(hostname) · $(python3 --version) · $(uname -m)"; ls /dev/i2c-1 >/dev/null 2>&1 && echo "I2C enabled" || echo "I2C NOT enabled: sudo raspi-config → Interface Options → I2C"; command -v i2cdetect >/dev/null && i2cdetect -y 1 | grep -q " 3c" && echo "OLED found at 0x3C" || echo "OLED not seen at 0x3C (check wiring/I2C, or install i2c-tools)"'

echo "== Copying the glasses client"
ssh_pi 'mkdir -p ~/aware/hardware ~/aware/wheels'
scp -q hardware/__init__.py hardware/display.py hardware/oled_client.py hardware/oled-assets.json "$PI:aware/hardware/"
scp -q .cache/pi-wheels/smbus2-*.whl "$PI:aware/wheels/" 2>/dev/null || true
ssh_pi 'python3 -c "import smbus2" 2>/dev/null && echo "smbus2 present" || (python3 -m pip install --user --no-index ~/aware/wheels/smbus2-*.whl 2>/dev/null || python3 -m pip install --user --break-system-packages --no-index ~/aware/wheels/smbus2-*.whl) && echo "smbus2 installed"'

if [ "$MODE" = selftest ]; then
  echo "== Self-test: six fake cues, then blank (about 15 s)"
  ssh_pi "cd ~/aware && python3 -m hardware.oled_client --sink ssd1306 --self-test --labels ${FLIP:-}"
else
  MAC_IP="${2:-$(ipconfig getifaddr en0)}"
  echo "== Following http://$MAC_IP:8766 (Ctrl+C stops; the OLED clears)"
  ssh_pi "cd ~/aware && python3 -m hardware.oled_client --receiver http://$MAC_IP:8766 --sink ssd1306 ${FLIP:-}"
fi
