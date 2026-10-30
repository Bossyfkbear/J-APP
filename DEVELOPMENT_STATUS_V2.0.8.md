# V2.0.8

- Adds explicit Windows real-model smoke-test command for installed denoise, Demucs separation, Beat This!, pYIN and WPE.
- Synthesizes 8 seconds of deterministic low-volume stereo fixture, runs real local inference, validates output format and finite samples, preserves input hash; no user audio and no model download.
- User-run optional AI environment; normal Windows CI tests only the fixture, missing-model handling, read-only listing and packaged helper, not neural inference.
- No claim of listening QA or U87 microphone calibration.
