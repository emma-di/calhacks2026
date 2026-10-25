# Two INMP441 microphones on the original Pi Zero W

Status: prepared and dry-run validated on the actual Pi (Raspbian 13.6, kernel 6.18.50 ARMv6).
**Physical capture has not yet been tested.** Administrator authentication and a reboot are pending.
The display and inference processes are not changed by this setup script.

## Interface

Both microphones share GPIO18 / BCLK (physical 12), GPIO19/WS (35), GPIO20/DIN (38), 3.3 V and ground.
One L/R input goes to ground, the other 3.3 V. Never connect both microphones to the same stereo slot.
The Pi supplies the clocks; the frame has two 32-bit slots. The first diagnostic capture uses
48 kHz signed 32-bit stereo. This alone does not establish useful direction accuracy.

The overlay uses `simple-audio-card` and the **already installed**, register-free
`snd-soc-ics43432` codec descriptor. The official driver explicitly supports similar I2S MEMS
microphones with 64 clocks per frame, 32 bits per channel and 24-bit data, and allows two capture
channels. This is an interface compatibility choice; the physical microphones remain INMP441s.
No external driver or replacement kernel is installed.

Evidence: [Raspberry Pi kernel codec source](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/sound/soc/codecs/ics43432.c),
[BCM2835 I2S source](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/sound/soc/bcm/bcm2835-i2s.c).
The VoiceHAT overlay was rejected because it also claims GPIO16 for an unrelated amplifier.
The ADAU7002 descriptor was rejected because there is no PDM converter in this build.

## Install, interactively on the Pi

Source and script are staged in `/home/pi/aware-mic-setup` on the currently tested Pi.
From the Mac, run:

```sh
ssh -t pi@glasses-pi.local 'sudo bash /home/pi/aware-mic-setup/apply.sh'
```

Enter the Pi account's administrator password at its own prompt. Do not put it in chat, scripts,
or shell arguments. The script makes a timestamped backup, installs the compiled overlay, and adds
an isolated `[all]` configuration block. It **does not reboot**. Coordinate reboot with whoever owns
the running display before doing it.

After reboot:

```sh
arecord -l
pinctrl get 18-21
arecord -D hw:CARD=AwareINMP441,DEV=0 --dump-hw-params -f S32_LE -r48000 -c2 -d1 /dev/null
```

Only after explicit permission to record, take a short private stereo recording. Check both channels
for nonzero levels and nonidentical samples, no ALSA overruns, and no clipping. Then label which
physical microphone occupies each slot by making a quiet sound near one microphone at a time.
Two live channels do not by themselves validate spatial localization.

## Roll back

The script prints the backup directory `/home/pi/aware-mic-backup-TIMESTAMP`.
Restore its `config.txt` to `/boot/firmware/config.txt` with administrator permission, then coordinate
a reboot. If an older overlay existed, its copy is in that same backup. A new orphaned `.dtbo` file
is harmless once the configuration line is removed. Never restore a stale configuration over later
teammate changes: compare the files first.

## Checks already performed

- `bash -n apply.sh` passes.
- Pi's installed `dtc` compiles `aware-inmp441-overlay.dts` without errors.
- Pi's `fdtoverlay` applies it to its shipped `bcm2708-rpi-zero-w.dtb` in a temporary output file.
- Resulting device tree reports I2S status `okay`, `AwareINMP441`, two 32-bit slots, CPU clock master.
- Required ICS43432, BCM2835 I2S and simple-card modules exist for the running kernel.
- Existing boot configuration and OLED were left unchanged during preparation.
