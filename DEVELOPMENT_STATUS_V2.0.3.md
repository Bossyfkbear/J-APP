# V2.0.3: manual sound output acceptance

Added low-volume 1-second stereo playback test to the Environment Check panel. Asks permission before playback and user yes/no after playback, with no mic access, recording or network. Self-test uses PortAudio/sounddevice and defaults to low -30 dBFS with 50ms fades. Automated tests verify output shape, level limits and input validation; they never use sound hardware. Physical playback verification requires user action on a Windows workstation.
