# Spidey Sense

*Visual cues for the sounds around you.*

## Inspiration

My aunt is hard of hearing, and growing up so close to her, I witnessed firsthand the challenges she faced in certain situations, such as evacuations, finding people in crowds, or interacting with strangers in public. The loss of this vital sense can greatly impact how you approach your daily decisions. 

In a survey of 201 deaf and hard-of-hearing people, safety sounds (alarms, sirens, approaching cars) topped the list. Next came attention-getting sounds: someone calling you, a knock, people nearby. Both what a sound is and where it comes from were rated "very interested." (Findlater et al., CHI 2019)

And one University of Washington study, **about half of deaf and hard-of-hearing participants reported missing an important sound every day.**

(https://par.nsf.gov/servlets/purl/10106339)

We wanted to make a wearable device that would alert deaf users of important sounds in their lives while also keeping this technology accessible. 
Prescription hearing aids average $3,432 per pair (HearingTracker, 2025) and don't help everyone, including many profoundly deaf people. Commercial assistive glasses cost $499 to $5,000, often with monthly subscriptions, and focus mostly on captions rather than the sounds around you (HearingTracker review). Spidey Sense takes a different approach.

## What it does

Spidey Sense creates visual cues for auditory inputs from the user's surroundings, counteracting a loss of hearing by depicting what direction sounds like voices, alarms, and approaching cars are coming from.

- **Name alerts:** notifies the user when someone nearby calls their name or nickname
- **Environmental sound alerts:** recognizes 527 types of everyday sounds, from smoke alarms to dog barks
- **Custom sounds:** lets users teach the glasses sounds unique to their home, such as their own doorbell
- **Direction finding:** shows which direction each sound is coming from
- **Priority modes:** Work and Do-not-disturb modes hold back lower-priority sounds, while urgent alerts like smoke alarms always come through

## How we built it

This project had both heavy software and hardware requirements.

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

### Two-Microphone Pseudo-Triangulation

With only two microphones, each auditory input has two plausible directions relative to the user. The microphones locate a sound by measuring the small difference in when it reaches each one, but a sound in front of the user and its mirror image behind the user produce the exact same delay. This makes it impossible to ascertain whether an input is in front of or behind the user.

To solve this issue, we first considered using the natural rotation of the user's head while walking to determine the location of the input. As the user turns, the delay between the microphones changes, and the direction of that change would reveal whether the sound came from the front or the back. However, without an IMU, we would not be able to know which direction the user turned their head, making the direction of the sound ambiguous once again.

Thus, we resorted to using the user's phone microphone as a third microphone. Because the phone sits in a different position from the two microphones on the glasses, it breaks the front-back symmetry and lets us verify the direction a signal is coming from.

## Challenges we ran into

- Assessing audio direction with only two microphones
- Customizing names, isolating
- Fine-tuning signal inputs to be readable and classifiable
- Creating an ergonomic product while maintaining functionality
- Hardware layout

## Accomplishments that we're proud of

- Building a working heads-up display for under $36 in parts
- Running both speech and sound classification models on a $10 Raspberry Pi Zero W
- Letting users teach the glasses a new sound in about a second from only five recordings
- Recognizing uncommon names by learning how the model actually hears them
- Resolving front-back ambiguity using the phone the user already carries

## What we learned

- Communicating between two I2S microphones through hardware
- Post-training on a 65 million parameter sound classification model
- Using resistors to clean audio data

## What's next for Spidey Sense

- Adding an IMU so head rotation can resolve sound direction without relying on the phone
- Testing with deaf and hard-of-hearing users, including measuring alert latency, alert accuracy, and comfort
- Slimming down the mount so it fits comfortably alongside hearing aids and cochlear implants
- Expanding name alerts into optional live captions for conversations
- Creating PCB design for the electrical layout to produce a more slim and ergonomic design for users

## References

- Jain et al., "Exploring Sound Awareness in the Home for People Who are Deaf or Hard of Hearing," *CHI 2019*. [Link](https://par.nsf.gov/servlets/purl/10106339)

## Running the code

- [Developer setup](docs/setup.md): run the mock alerts, the audio recognizer and the laptop monitor
- [Contributing](CONTRIBUTING.md): branches, pull requests and checks
- [Direction finding](spatial/README.md): the two-microphone sound map simulator
