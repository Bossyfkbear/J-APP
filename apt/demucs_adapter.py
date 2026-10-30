"""Local inference using the interfaces shipped in Demucs 4.0.1."""
from pathlib import Path


def infer(source, model_dir, model_name=None, cancelled=None):
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import convert_audio

    local = Path(model_dir).expanduser().resolve()
    if not local.is_dir():
        raise ValueError('Select a local Demucs model repository')
    names = sorted({p.stem for p in local.glob('*.yaml')} |
                   {p.stem.split('-')[0] for p in local.glob('*.th')})
    selected = model_name or ('htdemucs' if 'htdemucs' in names else
                              (names[0] if len(names) == 1 else None))
    if not selected or selected not in names:
        raise ValueError('Specify a local model name. Available: ' + ', '.join(names))
    def check_cancel():
        if cancelled and cancelled():
            raise RuntimeError('已取消')
    check_cancel()
    model = get_model(selected, repo=local).cpu().eval()
    raw, rate = sf.read(str(source), dtype='float32', always_2d=True)
    if not len(raw) or not np.isfinite(raw).all():
        raise ValueError('Input is empty or contains nonfinite audio')
    audio = convert_audio(torch.from_numpy(raw.T.copy()), rate,
                          model.samplerate, model.audio_channels)
    reference = audio.mean(0)
    mean, scale = reference.mean(), reference.std()
    if not torch.isfinite(scale) or scale.item() <= 1e-10:
        raise ValueError('Audio has insufficient variation for source separation')
    check_cancel()
    with torch.no_grad():
        predicted = apply_model(model, ((audio - mean) / scale)[None],
                                device='cpu', shifts=0, split=True,
                                overlap=0.25, progress=False, num_workers=0)[0]
        predicted = predicted * scale + mean
    check_cancel()
    expected = (len(model.sources), audio.shape[0], audio.shape[1])
    if tuple(predicted.shape) != expected or not torch.isfinite(predicted).all():
        raise ValueError('Demucs returned invalid shape or nonfinite samples')
    return audio, dict(zip(model.sources, predicted)), int(model.samplerate), selected
