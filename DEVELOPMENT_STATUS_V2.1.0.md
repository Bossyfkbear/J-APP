# V2.1.0

- Connect real optional model smoke script to Environment Check GUI: choose denoise/split/meter/pitch/dereverb and explicitly opt into 8s synthetic inference.
- External .apt-ai Python runs in a cancellable Windows process tree with a 15-minute timeout. Report streamed to the existing process log. No customer audio, automatic installs or network required.
- Does not automatically call model verification in GitHub Actions, since the optional multi-gigabyte dependencies and weights are not installed in the core CI.
- Device sound, calibrated U87 and real-recording perceptual acceptance remain user workstation validations.
