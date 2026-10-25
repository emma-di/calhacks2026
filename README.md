# Spidey Sense

*Visual cues for the sounds around you.*

## Inspiration

Yameen's aunt is hard of hearing, and growing up so close to her, he witnessed firsthand the challenges she faced during evacuations, finding people in crowds, or interacting with strangers in public. The loss of this vital sense can greatly impact how you approach your daily decisions.

In a survey of 201 deaf and hard-of-hearing people, safety sounds (alarms, sirens, approaching cars) topped the list. Next came attention-getting sounds: someone calling you, a knock, people nearby. Both what a sound is and where it comes from were rated "very interested." (Findlater et al., CHI 2019)

In one University of Washington study, **about half of deaf and hard-of-hearing participants reported missing an important sound every day.** (Bragg et al., ASSETS 2016)

We wanted to make a wearable device that would alert deaf users of important sounds in their lives while also keeping this technology accessible. Prescription hearing aids average $3,432 per pair (HearingTracker, 2025) and don't help everyone, including many profoundly deaf people. Commercial assistive glasses cost $499 to $5,000, often with monthly subscriptions, and focus mostly on captions rather than the sounds around you (HearingTracker review). Spidey Sense takes a different approach.

## What it does

Spidey Sense creates visual cues for auditory inputs from the user's surroundings, counteracting a loss of hearing by depicting what direction sounds like voices, alarms, and approaching cars are coming from.

- **Name alerts:** notifies the user when someone nearby calls their name or nickname
- **Environmental sound alerts:** recognizes 527 types of everyday sounds, from smoke alarms to dog barks
- **Custom sounds:** lets users teach the glasses sounds unique to their home, such as their own doorbell
- **Direction finding:** shows which direction each sound is coming from
- **Priority modes:** Work and Do-not-disturb modes hold back lower-priority sounds, while urgent alerts like smoke alarms always come through
- **Private by design:** all recognition runs locally, and raw microphone audio is never saved or uploaded

## How we built it

This project had both heavy software and hardware requirements.

### System Overview

Every sound follows the same path through our system. Audio from the microphones is converted to 16 kHz mono and passed to a local recognition model. When a sound is recognized, the model produces a small event containing the sound's type, label, confidence score, priority tier, timestamp, and direction. That event is sent to our alert engine, which decides whether it should be shown, and the active alert is finally rendered on the glasses display.

**Sound → local recognition → event → priority rules → glasses cue**

Because every part of the system speaks the same event format, our hardware, machine learning, and interface teams were able to work in parallel. Before the glasses were ready, we tested the entire pipeline using a browser-based monitor that simulates the display, along with mock events for each sound.

### Hardware

Physically, we 3D printed a mount that is meant to be placed on the glasses. The mount holds together our electrical components: a $10 Raspberry Pi Zero W and a $2 OLED display. The mount also holds a reflective mirror that concentrates all of the display light through an optical lens, which is lastly presented on a translucent beam splitter in front of the eyes. On the arms of the glasses are the microphones, one on the left and one on the right. The microphones constantly stream audio data to the Pi, so that relevant sounds can be classified.

| Component | Cost |
|---|---:|
| Raspberry Pi Zero W | $10.00 |
| OLED Display | $2.20 |
| INMP441 Microphones | $6.10 |
| 3D Print | $7.40 |
| Wiring, resistors, lens | $10.00 |
| **Total** | **$35.70** |

### Speech Model

To alert the user when someone calls their name, we run a streaming keyword spotter, which is a small 3.3-million-parameter speech model from the sherpa-onnx Zipformer family. Rather than transcribing everything said around the user, which would be slow, power-hungry, and a privacy concern, the model listens only for the user's name and nicknames, which are entered once in the companion app. Audio is fed to the model in 0.2-second chunks, allowing an alert to appear at about the same time the name finishes being spoken.

However, because the model spells words using a small vocabulary of about 500 word fragments, it often interprets uncommon names differently than they are written. For example, the base model hears "Yameen" as "YEMY." To solve this issue, we allow the user to have a friend say their name a few times. The model transcribes those recordings using its own fragments, and we add what it heard as additional keywords. Thus, the model learns to recognize the name the way it actually hears it. Spellings that are common English words, such as "why" for Wei, are rejected, since they would trigger constantly during normal conversation.

### Audio Classification Model

For environmental sounds, we use **Zipformer Small**, a compact audio-tagging model trained on Google's AudioSet that recognizes 527 different sound types. Every second, the model analyzes the most recent two seconds of audio. Per-sound thresholds, cooldowns, and suppression rules then convert its scores into alerts, ensuring that a fading alarm, for example, is not reported again as a "bell."

However, since every home sounds different, we also allow users to teach the system their own sounds. To do this, we extract the model's internal 256-number "fingerprint" of each sound and train a small classifier on about five recordings of a sound, such as the user's doorbell. These recordings are compared against a bank of everyday background noise and, optionally, a recording of the user's own room. Training takes about a second, allowing the new sound to start working on the live microphone immediately.

Every alert is then sent to a **priority engine**, which decides what reaches the glasses. A smoke alarm will always interrupt the user, while a dog bark can be skipped. Thus, users can enable **Work** and **Do-not-disturb** modes to hold back lower-priority sounds.

### Alert Priority Tiers

Each sound is assigned a priority tier, which determines whether it can interrupt the alert currently on screen and how long it stays visible. A new alert only replaces the current one if it is of equal or higher priority, so a dog bark can never cover up a smoke alarm.

| Tier | Example sounds | Time on display |
|---|---|---:|
| 4 (critical) | Smoke alarm | Up to 30 s, or until dismissed |
| 3 (urgent) | Siren, someone calling your name | 5 s |
| 2 (attention) | Door knock, bell or chime, alarm clock | 3 s |
| 1 (awareness) | Dog barking | 2 s |
| 0 (ignored) | Sounds the user has turned off | Not shown |

Each sound type also has a five-second cooldown, so a dog that barks continuously produces one alert instead of a constant stream.

### Choosing and Testing the Model

We originally built the system around Google's **YAMNet** model, then compared it against **Zipformer Small** on the same benchmark. To avoid fooling ourselves, we tuned every threshold on one set of recordings (ESC-50 folds 1–3) and measured results on a separate, held-out set (folds 4–5), keeping all recordings by the same author in the same split. We then tested each recording in four conditions: clean, quiet, with added background noise at +10 dB SNR, and with a synthetic echo, giving us **418 recordings and 1,672 test cases**.

YAMNet was faster, at about 2 ms per window compared to Zipformer's 14 ms, but it struggled in noise. Zipformer's two-second context window held up far better, so we chose it as our default.

| Sound (in added noise) | YAMNet recall | Zipformer recall |
|---|---:|---:|
| Door knock | 43.8% | 81.2% |
| Dog barking | 75.0% | 93.8% |
| Siren | 68.8% | 100.0% |
| Alarm clock | 81.2% | 81.2% |

Our final held-out results with Zipformer are below. Hits are counted per recording.

| Sound | Clean hits | Noisy hits | Clean false alerts |
|---|---:|---:|---:|
| Dog barking | 16/16 | 15/16 | 0/152 |
| Door knock | 15/16 | 13/16 | 1/152 |
| Siren | 16/16 | 16/16 | 0/152 |
| Alarm clock | 15/16 | 13/16 | 1/152 |
| Smoke alarm | 7/7 | 7/7 | 0/161 |
| Bell / chime | 7/7 | 6/7 | 3/161 |

Median inference time was **13.9 ms** per window, with a 95th percentile of 30.8 ms, which is well within our one-second update interval.

Benchmarking also showed us where the system was weak. Our original bell rule caught a bell in only 4 of 7 noisy recordings, so we expanded it to include the model's Bell, Ding, and Chime labels, raising this to 6 of 7. In echo, the bell rule also produced 5 false alerts, mostly from the fading tails of alarms. To solve this issue, we added a suppression rule. When an alarm clock, smoke alarm, or siren is recognized, the bell cue is held back for four seconds afterward, which reduced echo false alerts from 5 to 0. Finally, because bicycle bell detection failed on every held-out recording, we disabled it rather than show users an alert we could not trust.

### Two-Microphone Pseudo-Triangulation

With only two microphones, each auditory input has two plausible directions relative to the user. The microphones locate a sound by measuring the small difference in when it reaches each one, but a sound in front of the user and its mirror image behind the user produce the exact same delay. This makes it impossible to ascertain whether an input is in front of or behind the user.

To solve this issue, we first considered using the natural rotation of the user's head while walking to determine the location of the input. As the user turns, the delay between the microphones changes, and the direction of that change would reveal whether the sound came from the front or the back. However, without an IMU, we would not be able to know which direction the user turned their head, making the direction of the sound ambiguous once again.

Thus, we resorted to using the user's phone microphone as a third microphone. Because the phone sits in a different position from the two microphones on the glasses, it breaks the front-back symmetry and lets us verify the direction a signal is coming from.

### Privacy and Reliability

All recognition runs locally, so no audio is ever sent to the cloud. Raw microphone audio is never saved, and the name detector only listens for the user's chosen keywords rather than transcribing conversations. For debugging, the system keeps decision logs that record only scores, thresholds, timestamps, and the reason each alert was shown or suppressed. These logs let us trace exactly why a sound did or did not trigger an alert. The codebase also includes unit tests and multi-event simulations, such as overlapping, repeated, and back-to-back sounds, which run automatically on every pull request.

## Challenges we ran into

- Assessing audio direction with only two microphones
- Customizing names, isolating
- Fine-tuning signal inputs to be readable and classifiable
- Creating an ergonomic product while maintaining functionality
- Hardware layout
- Keeping recognition accurate in background noise, where our first model missed over half of door knocks
- Preventing a fading alarm from being reported a second time as a bell
- Bicycle bell detection that never worked reliably, which we chose to disable

## Accomplishments that we're proud of

- Building a working heads-up display for under $36 in parts
- Running both speech and sound classification models on a $10 Raspberry Pi Zero W
- Letting users teach the glasses a new sound in about a second from only five recordings
- Recognizing uncommon names by learning how the model actually hears them
- Resolving front-back ambiguity using the phone the user already carries
- Benchmarking our system on 1,672 held-out test cases, with 100% detection of smoke alarms and sirens in clean audio and added noise
- Cutting false bell alerts in echo from 5 to 0 with a context-aware suppression rule
- Keeping the system fully local and private, with no audio saved or uploaded

## What we learned

- Communicating between two I2S microphones through hardware
- Post-training on a 65 million parameter sound classification model
- Using resistors to clean audio data
- Separating tuning and test data so our accuracy numbers reflect how the system performs on sounds it has never seen
- Designing a shared event format so hardware, machine learning, and interface work could happen in parallel
- Weighing speed against accuracy when choosing between models

## What's next for Spidey Sense

- Adding an IMU so head rotation can resolve sound direction without relying on the phone
- Testing with deaf and hard-of-hearing users, including measuring alert latency, alert accuracy, and comfort
- Slimming down the mount so it fits comfortably alongside hearing aids and cochlear implants
- Expanding name alerts into optional live captions for conversations
- Creating PCB design for the electrical layout to produce a more slim and ergonomic design for users
- Testing smoke alarm detection with more recordings and in real rooms, since our current evidence comes from only 11 recordings

## References

- Findlater et al., "Deaf and Hard-of-hearing Individuals' Preferences for Wearable and Mobile Sound Awareness Technologies," *CHI 2019*. [Link](https://par.nsf.gov/servlets/purl/10106042)
- Bragg et al., "A Personalizable Mobile Sound Detector App Design for Deaf and Hard-of-Hearing Users," *ASSETS 2016*.
- Jain et al., "Exploring Sound Awareness in the Home for People Who are Deaf or Hard of Hearing," *CHI 2019*. [Link](https://par.nsf.gov/servlets/purl/10106339)
- HearingTracker, hearing aid pricing data, 2025.
- Piczak, "ESC-50: Dataset for Environmental Sound Classification." [Link](https://github.com/karolpiczak/ESC-50)
- k2-fsa, sherpa-onnx pretrained audio-tagging models. [Link](https://k2-fsa.github.io/sherpa/onnx/audio-tagging/pretrained_models.html)

## Running the code

- [Try it in your browser](https://emma-di.github.io/calhacks2026/): test sounds, no install
- [Demo and setup guide](docs/demo.md): what to look for, and how to run the live microphones on a laptop
- [Contributing](CONTRIBUTING.md): branches, pull requests and checks
- [Direction finding simulator](spatial/README.md): the two-microphone sound map
- [Team notes](TEAM-NOTES.md) and [work status](WORK-STATUS.md): handoffs and current readiness
