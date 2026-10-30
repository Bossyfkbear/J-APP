# Audio Post Toolkit V1.9.9

Fixed automatic PCM depth in the filter path, including CLI. Preserves known 24-bit PCM, float32 and float64 subtypes when `--depth auto`; uses PCM24 fallback for compressed/unknown sources. Added two real FFmpeg regression tests. Native Windows audio device acceptance and U87 model calibration remain outstanding.
