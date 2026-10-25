# Next direction calibration and acceptance

The real Pi audio → recognition → browser/OLED path has worked. The 17-event calibrated alarm
trial demonstrated both lateral cues, not measured localization accuracy. More calibration and
controlled acceptance are useful; making the threshold smaller is not a substitute.

## Latest mounted result: not accepted

User still reports inaccurate direction after the provisional mounted gain offset−3.85dB
replaced−0.89dB. Most sampled frames were level-based rather than arrival-time-based. The
correction changed the side bias; it is not a passed calibration. A left/right broadband-clap
check and sound-port inspection are the current diagnostic. Existing numeric `.cache/` values
are local only; verify actual loaded values before testing.

## Mount first

1. Fix microphones in their final positions. Measure opening-to-opening separation accurately;
   the current front-angle calculation uses nominal12cm and a13cm lag bound.
2. Confirm channel0 is still physical left and1 right. Keep optics mirroring separate from
   acoustic left/right; an OLED `--flip-x` must not silently invert the acoustic coordinate frame.
3. Keep the same speaker, volume and height during each comparison. Recheck a centered reference
   at normal listening distance before changing the local gain offset (latest provisional mounted value−3.85dB).
4. A gain offset does not calibrate timing offset, mic frequency response or head-shadow effects.
   Those remain unmeasured. Do not tune against the same trials then report them as held-out accuracy.

## Controlled test matrix

Use positions−90°,−45°,0°,+45°,+90° relative to the wearer's face. Test at1m and3m, three repeats
per position/distance, keeping the wearer's head still. That is30 placements per sound. Use an
alarm first, then a broadband sound such as a knock/clap from the source location. Record numeric
results only; no raw audio is required. Timestamp the actual position changes explicitly.

Record separately:

- Expected position, distance, trial number and recognized sound event.
- Predicted angle, whether it was timing-based/level-based/assumed-front, and time to display.
- Correct side, wrong side and assumed-front counts. Do not count an assumed front as measured
  front/back resolution, even when the speaker happened to be in front.
- Flip/chatter during each stationary trial. Check the OLED against the browser simultaneously.
- Missed sound detections separately from localization failures; a silent display is not proof
  of a spatial failure. Current name cues assume front because their speech intervals are not
  localized; do not include them as measured direction successes.

Then repeat a small subset with room noise, wearer movement and two competing sources. Keep rear
positions out of a claimed accuracy score: current demo deliberately assumes a front hemisphere.

## Other physical acceptance still needed

- Correct horizontal/vertical OLED orientation through the final reflector, legibility and brightness.
- Disconnect/reconnect and service restart: meters/old arrows clear, calibration values actually
  reload, Pi capture/display recover, no second capture/display owner starts.
- Repeat suppression is OFF for testing. Explicitly choose the demo setting afterward and verify
  repeated alerts and changing directions with that setting; do not assume test mode is production behavior.
- If moving inference to another Mac, transfer/recreate numeric calibration and dependencies;
  `.cache/pi-spatial-calibration.json` is local and not part of a normal Git clone.

Do not mark full readiness from unit tests or one successful sound. Current software verification
is80 Python checks plus58 frontend checks and a successful build; final mounted-room acceptance
is distinct. See [runtime policy and evidence](rough-front-angles.md).
