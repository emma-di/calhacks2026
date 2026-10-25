#!/usr/bin/env bash
# Run interactively on the Pi with sudo bash /home/pi/aware-mic-setup/apply.sh.
# Backs up before adding only the microphone overlay. Does not reboot.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Administrator access required; run this script with sudo on the Pi.' >&2
  exit 1
fi
setup_dir="$(cd "$(dirname "$0")" && pwd)"
boot_config=/boot/firmware/config.txt
boot_overlay=/boot/firmware/overlays/aware-inmp441.dtbo
if grep -Eq '^[[:space:]]*dtoverlay=aware-inmp441([[:space:]]|$)' "$boot_config"; then
  echo 'Aware microphone overlay already configured. No changes made.'
  exit 0
fi
dtc -@ -I dts -O dtb -o "$setup_dir/aware-inmp441.dtbo" "$setup_dir/aware-inmp441-overlay.dts"
task_stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="/home/pi/aware-mic-backup-$task_stamp"
mkdir -m 700 "$backup_dir"
cp -p "$boot_config" "$backup_dir/config.txt"
if [ -e "$boot_overlay" ]; then cp -p "$boot_overlay" "$backup_dir/aware-inmp441.dtbo"; fi
install -m 644 "$setup_dir/aware-inmp441.dtbo" "$boot_overlay"
cat >> "$boot_config" <<'CONFIG'

[all]
# Aware: two shared-clock INMP441s, opposite L/R slots; Pi capture only.
dtparam=i2s=on
dtoverlay=aware-inmp441
CONFIG
printf 'Microphone overlay configured. Original config: %s/config.txt\n' "$backup_dir"
echo 'No reboot performed. Reboot when ready, then check arecord -l.'
