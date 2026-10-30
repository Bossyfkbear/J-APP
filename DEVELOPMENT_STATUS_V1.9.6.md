# V1.9.6 milestone

- Adds reference-based microphone tone matching with bounded EQ and a linear-phase FIR in the existing desktop UI; no extra mandatory dependencies beyond NumPy and SoundFile.
- Existing U87-inspired EQ retained when no reference is chosen. A specific real U87 microphone model cannot be claimed without calibrated paired recordings.
- Full-file mono/stereo processing preserves sample rate, channel count, duration; exports float32 WAV. Staged non-overwriting file publication and cancellation checks.
- Synthetic regression coverage: tonal change, stereo and source hash, invalid reference, cancellation, and zero-strength identity.
- Release dependencies remain modular. Native Windows audio playback and user-recording quality sign-off outstanding.
