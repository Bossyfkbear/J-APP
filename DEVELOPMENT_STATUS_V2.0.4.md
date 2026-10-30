# V2.0.4

- User-triggered output test uses the default audio device's actual sample rate and verifies stereo output settings before playing.
- CI tests mock 44.1 kHz output device without physical playback. Never claims actual audible output without user confirmation.
