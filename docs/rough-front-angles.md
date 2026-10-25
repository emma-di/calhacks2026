# Current demo: eight direction buckets, front hemisphere assumed

October25 user decisions supersede earlier unknown-only/16-live-position notes:

- Keep phone out of the current capture array; prioritize the two Pi microphones.
- Assume front when ambiguous, and use the front branch in angle calculations.
- Eight buckets are sufficient: four cardinal positions plus four diagonals.
- Leave optical flipping until after spatial testing. `hardware.oled_client --flip-x` and
  `--flip-y` already exist; neither is enabled by this spatial change.

Current `audio/pi_spatial.py` uses the measured GCC-PHAT lag and nominal12cm spacing to estimate
`asin(lag*343/(48000*.12))`, bounded to the front hemisphere. 13cm remains the physical lag upper
bound because actual spacing is approximately11–13cm. Aggregate with a median and round to45°.
That permits front,left/right diagonals,left,right. Rear buckets remain supported by the renderer
but cannot be measured by this array. Level-only evidence gives a rough ±45° side, not a volume
to angle formula. When a recognized event is unresolved, the user-approved fallback is0° with
`direction_assumed_front=true` and an `assumed_front:*` reason. This is an assumption, not measured
front/back. Invalid/offline meters still clear; silence does not itself create an event or an arrow.

Current sensitivity: level margin1.25dB, louder channel >=−75dBFS, both channels >=−85dBFS,
coherence>=.2; timing requires coherence>=.55 and peak ratio>=1.6. Window needs2 supporting100ms
frames and65% agreement among directional frames. Contradictory level/timing signs veto only when
level difference is>=3dB. Existing temporal and quiet-gap rules still apply. Thresholds are
experimental; low differences can reflect gain mismatch or noise, and wrong-side rates remain
unmeasured. Recalibrate with a known centered source before stronger accuracy claims.

**Latest actual runtime:** centered-alarm reference measured right channel0.89dB louder
(38 audible numeric samples, median left-minus-right−0.89dB). Mac-local
`.cache/pi-spatial-calibration.json` now stores schema_version1, gain_offset_db−0.89, margin_db0.75.
`audio/pi_input.py` loads bounded numeric values at startup; missing/invalid calibration falls back
to0dB offset/1.25dB margin. The active feed `/pi-audio/levels` includes `spatial_calibration` so loading
is verifiable. This calibration is not automatically transferred to another Mac; remeasure if
microphone positions/gains or sound setup change. No raw audio saved.

An inherited ignored SIGINT meant several earlier reload requests failed: the old worker retained
port8768 and new workers could not load changed settings. The stale worker was terminated and the
replacement verified via its new calibration telemetry. `audio.cli` now explicitly handles SIGINT
and SIGTERM as graceful shutdown. **Always confirm loaded settings, not just that the feed is live.**

Physical integration evidence:

- Real OLED detected atI²C0x3C, current renderer deployed with `scripts/glasses_up.sh live`.
- Dancing Bear `/home/pi/oled_hello_bear.py` PID1076 was competing for the display. User authorized
  pausing it; SIGSTOP confirmed stateT. Resume only if wanted via SIGCONT to the verified process.
- User confirmed the real display works. During live microphone test,149/149 sampled active
  state/display event IDs matched. Real Fire/smoke alerts appeared at0° and+45°. This proves the
  live path, not localization accuracy. User reported too many front fallbacks; sensitivity was
  increased afterward and still needs directional acceptance.
- First mock direction sequences merged repeats, so only their first angle was confirmed. Do not
  report all three mock positions as a pass. Repeat suppression is now OFF for live hardware
  testing, allowing repeated detections to replace the displayed cue.
- Receiver8766 and OLED polling stay running; Pi model worker was restarted for current settings.
  No microphone models/frontend were installed on Pi. Raw audio was not saved during these trials.

Tests cover known signed delays, all five attainable front-hemisphere buckets, explicit fallback,
quiet/dropout, event association and renderer compatibility. Real-room left/right accuracy remains
open. A farther sound loses simple distance-related level contrast, but far-field timing difference
is still approximately spacing*sin(angle)/sound-speed; echoes and reducedSNR make it harder to use.
