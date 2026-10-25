# Glasses session checklist (Pi + SSD1306)

1. Mac on the Pi's network (the hotspot it uses); `ping glasses-pi.local` answers. Key login is set up.
2. Pause Yameen's bear demo while we use the display: `ssh pi@glasses-pi.local 'kill -STOP $(pgrep -f oled_hello_bear.py)'`.
3. `scripts/glasses_up.sh selftest` — deploys the latest client (prints "Pi now runs: <commit>") and shows six cues.
4. **Optics review:** `SECONDS_PER=3 scripts/glasses_up.sh gallery` — all 50 cue icons (names print in the
   terminal), the four tier styles, then 16 arrow positions. Note per icon: readable through the combiner?
   Try `FLIP=--flip-x` if mirrored, and brightness with `OLED_ARGS="--contrast 255"` (or lower).
5. **Live:** `scripts/glasses_up.sh live` (receiver must run on the Mac at 127.0.0.1:8766; tunnelled over SSH).
6. Done: Ctrl-C, then restore the bear: `ssh pi@glasses-pi.local 'kill -CONT $(pgrep -f oled_hello_bear.py)'`.
