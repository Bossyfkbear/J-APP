# V2.0.9

Windows source regression fix: read the UTF-8 technical acceptance JSON explicitly using `encoding='utf-8'`, rather than cp1252. Previously the source suite yielded 109 pass, one fail solely in this QA test; no actual PCM processing failure. The Windows build will rerun the full suite including frozen GUI/audio checks.
