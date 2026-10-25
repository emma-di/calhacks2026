#!/usr/bin/env bash
# Put the glasses client on the Pi and drive the real SSD1306.
#   scripts/glasses_up.sh selftest            copy + install + fake cues on the OLED (no network to the Mac needed)
#   scripts/glasses_up.sh gallery             optics review: all 50 cue icons, 4 tier styles, 16 arrow positions
#   scripts/glasses_up.sh live                follow this Mac's receiver (127.0.0.1:8766) through an SSH tunnel:
#                                             the receiver is never exposed to the network
# Env: PI=pi@glasses-pi.local  FLIP="--flip-x" (if the combiner mirrors the image)
#      OLED_ARGS="--contrast 255" (extra client flags, e.g. brightness)  SECONDS_PER=3 (gallery pace)
set -euo pipefail
cd "$(dirname "$0")/.."
PI="${PI:-pi@glasses-pi.local}"
MODE="${1:-selftest}"
ssh_pi() { ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$PI" "$@"; }

echo "== Checking $PI"
ssh_pi 'echo "$(hostname) · $(python3 --version) · $(uname -m)"; ls /dev/i2c-1 >/dev/null 2>&1 && echo "I2C enabled" || echo "I2C NOT enabled: sudo raspi-config → Interface Options → I2C"'

echo "== Copying the glasses client"
ssh_pi 'mkdir -p ~/aware/hardware ~/aware/wheels'
scp -q hardware/__init__.py hardware/display.py hardware/oled_client.py hardware/oled-assets.json "$PI:aware/hardware/"
# Stamp what is deployed so the Pi's code version is never a guess.
echo "$(git rev-parse --short HEAD)$(git diff --quiet -- hardware || echo '+local-changes') $(date '+%Y-%m-%d %H:%M')" | ssh_pi 'cat > ~/aware/VERSION'
ssh_pi 'echo "Pi now runs: $(cat ~/aware/VERSION)"'
scp -q .cache/pi-wheels/smbus2-*.whl "$PI:aware/wheels/" 2>/dev/null || true
ssh_pi 'if python3 -c "import smbus2" 2>/dev/null; then echo "smbus2 present"; else python3 -m pip install --user --no-index ~/aware/wheels/smbus2-*.whl 2>/dev/null || python3 -m pip install --user --break-system-packages --no-index ~/aware/wheels/smbus2-*.whl; echo "smbus2 installed"; fi'
# Probe the bus with smbus2 itself (i2c-tools is often not installed).
ssh_pi 'python3 -c "
from smbus2 import SMBus
with SMBus(1) as bus:
    try:
        bus.read_byte(0x3C); print(\"OLED answering at 0x3C\")
    except OSError:
        print(\"Nothing at 0x3C: check OLED wiring (SDA pin 3, SCL pin 5, 3.3 V, GND)\")"'

if [ "$MODE" = selftest ]; then
  echo "== Self-test: six fake cues, then blank (about 15 s)"
  ssh_pi "cd ~/aware && python3 -m hardware.oled_client --sink ssd1306 --self-test --labels ${FLIP:-} ${OLED_ARGS:-}"
elif [ "$MODE" = gallery ]; then
  echo "== Gallery: 50 icons, 4 tiers, 16 arrows at ${SECONDS_PER:-2} s each (Ctrl+C stops)"
  ssh_pi "cd ~/aware && python3 -m hardware.oled_client --sink ssd1306 --gallery --gallery-seconds ${SECONDS_PER:-2} ${FLIP:-} ${OLED_ARGS:-}"
else
  # The Pi's 127.0.0.1:8766 is forwarded over this SSH session to the Mac's local receiver.
  echo "== Following the Mac receiver through SSH (Ctrl+C stops; the OLED clears)"
  ssh -o ConnectTimeout=8 -o ExitOnForwardFailure=yes -R 8766:127.0.0.1:8766 "$PI" \
    "cd ~/aware && python3 -m hardware.oled_client --receiver http://127.0.0.1:8766 --sink ssd1306 ${FLIP:-} ${OLED_ARGS:-}"
fi
