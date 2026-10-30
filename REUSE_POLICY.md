# Implementation policy

Use maintained, license-compatible upstream components before writing a new
audio algorithm. Keep the original desktop UI and independent module structure.

| Function | Existing implementation used |
| --- | --- |
| Speech denoise | DeepFilterNet3 |
| Source separation | Demucs htdemucs |
| Late-reverb reduction | NARA-WPE |
| Monophonic pitch | librosa pYIN |
| Beats and downbeats | Beat This! official pretrained model |
| Conversion, repairs, loudness | FFmpeg |
| Playback | sounddevice / PortAudio |
| Windows packaging | PyInstaller; optional GitHub Actions runner |

Application code handles parameters, offline loading, cancellation, file
protection, reports and GUI integration. Retain upstream notices. Publicly
viewable code without reuse permission is not treated as freely licensed.
Existing experimental key/chord modules are retained for compatibility; they
are not represented as trained, validated state-of-the-art models.
