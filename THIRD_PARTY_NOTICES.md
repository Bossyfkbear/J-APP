# Third-party components and model provenance

This personal-use source archive contains application code, not model weights,
FFmpeg binaries or a bundled AI runtime. Installing optional packages retrieves
their own distributions. No commercial redistribution clearance is claimed.

## Sources checked

- Beat This! 1.1.0: official source code AND published model weights are MIT,
  per https://github.com/CPJKU/beat_this#license . Uses upstream Audio2Beats and
  the minimal postprocessor (not madmom). The author separately notes that
  training recordings have their own rights; no training recordings are bundled.
  Official final0 checkpoint source and SHA256 are recorded in download_models.py.

- DeepFilterNet code: MIT OR Apache-2.0, as stated by the author:
  https://github.com/Rikorose/DeepFilterNet#license
  Official model archives: https://github.com/Rikorose/DeepFilterNet/tree/main/models
- Demucs: MIT, upstream license:
  https://github.com/facebookresearch/demucs/blob/main/LICENSE
  Official model locations are listed in the Demucs 4.0.1 package's
  `demucs/remote/files.txt`; supplied local checkpoint checksum suffixes are
  verified by Demucs. Only load model files from a trusted source: older Torch
  checkpoint formats can contain executable Python objects.
- FFmpeg: its license depends on build options and linked components:
  https://ffmpeg.org/legal.html . This application calls external executables.
  FFmpeg, FFprobe and FFplay are not included in this archive or copied by the
  Windows build script. If distributing them later, retain the exact build's
  licenses, corresponding source and build configuration.
- NARA-WPE (optional dereverberation): MIT:
  https://github.com/fgnt/nara_wpe/blob/master/LICENSE
- librosa (optional pYIN pitch analysis): ISC; see the installed distribution's
  license and https://github.com/librosa/librosa .
- The validation speech is an excerpt from LibriSpeech recording 5703-47212-0000,
  *Ashiel Mystery — A Detective Story*, chapter 2, narrated by Garth Comira.
  Source: https://librosa.org/data/audio/5703-47212-0000.ogg via librosa `libri1`;
  collection: https://www.openslr.org/12/ ; license: CC BY 4.0,
  https://creativecommons.org/licenses/by/4.0/ . Validation derivatives select
  the first approximately eight seconds, resample/scale it, add deterministic
  white noise, and apply DeepFilterNet. See `validation/VALIDATION.md`.

## Build records

The Windows staging script copies license/notice files available in installed
Python distributions and records package versions in `build-dependencies.json`.
That file is a build-environment inventory, not a complete legal review or a
claim that every installed package is shipped in the EXE. NumPy, SoundFile,
libsndfile, sounddevice, PortAudio, Python/Tcl/Tk and the PyInstaller bootloader
can have separate notices; retain bundled license files and review the actual
native build before public distribution. Python-package metadata alone does not
establish every native-library or model-weight permission.

No endorsement or measured equivalence to a Neumann U87 is claimed. The existing
microphone preset is labelled as an EQ experiment. Audio content must be owned
by the user or otherwise authorized for the processing performed.
