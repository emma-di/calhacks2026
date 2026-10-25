# Two INMP441 microphones on the original Pi Zero W

Status: installed and physically captured on October 25 on the actual Pi
(Raspbian 13.6, kernel 6.18.50 ARMv6). `AwareINMP441` appears as card 1, capture device 0.
A five-second stereo recording completed successfully; physical left/right slot mapping remains pending.
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
- After administrator installation and coordinated reboot, a real capture completed with 240,000
  stereo frames at 48 kHz, signed 32-bit little endian, exactly five seconds.
- Channel 0: RMS −41.88 dBFS, peak −15.85 dBFS. Channel 1: RMS −42.66 dBFS, peak −18.21 dBFS.
- Both channels contain positive and negative samples and are not byte-identical; correlation 0.881.
- No clipping, no all-zero 10 ms blocks, and no ALSA overrun messages in this short trial. These
  checks do not establish long-run reliability or useful localization accuracy.
- Private capture and diagnostic values are under ignored `.cache/pi-audio-tests/`; never commit audio.
- Actual pre-install boot backup: `/home/pi/aware-mic-backup-20261025-000106/config.txt`.
- Still needed: sound near each microphone to identify which physical side occupies each slot, then
  a separate synchronized spatial test with measured microphone spacing.

## Physical microphone check — October 25

A 20-second authorized stereo recording captured 960,000 frames at 48 kHz/S32_LE. During speech close
to the first microphone, channel 0 was up to 14.82 dB louder; near the other, channel 1 was up to 21.65 dB
louder. Both microphones therefore respond independently; these are not duplicated mono channels.
Physical left/right identity was not specified during the trial. Direction/calibration is a separate
step. No overruns were reported. Raw recordings remain private/ignored; sanitized result:
[pi-stereo-mic-check.json](../../reports/pi-stereo-mic-check.json).
