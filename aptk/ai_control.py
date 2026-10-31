"""Safe, modular, user-approved local AI runtime management.

No command runs at module import. A model is never downloaded implicitly.
"""
from pathlib import Path
import os

MODELS = {"denoise": "DeepFilterNet3", "split": "Demucs", "meter": "BeatThis"}


def installed_model_dir(operation, requested=None, *, root=None):
    """Resolve a manually selected model, else the installed canonical model."""
    if requested and str(requested).strip():
        return str(Path(requested).expanduser().resolve())
    if operation not in MODELS:
        return None
    if root is None:
        from apt.worker import app_directory
        root = app_directory()
    candidate = Path(root) / "models" / MODELS[operation]
    return str(candidate.resolve()) if candidate.is_dir() else None


def install_command(root, module, *, download_models=False, platform=None):
    """Produce an explicit subprocess argv; no shell interpolated from user data."""
    if module not in ("denoise", "split", "meter", "pitch", "dereverb"):
        raise ValueError("Unsupported optional AI module")
    platform = os.name if platform is None else platform
    if platform != "nt":
        raise RuntimeError("One-click installer currently supports Windows only")
    root = Path(root)
    script = root / "setup_ai_windows.bat"
    if not script.is_file():
        raise FileNotFoundError("Missing setup_ai_windows.bat in the release folder")
    if download_models and module not in MODELS:
        raise ValueError("Selected DSP tool does not require neural weights")
    argv = ["cmd.exe", "/d", "/c", str(script), "--module", module]
    if download_models:
        argv.append("--with-models")
    return argv


def external_popen(args, **kwargs):
    """Launch external Python/cmd without frozen PyInstaller DLL-path pollution.

    The running Windows EXE changes the process DLL search path; that inherited
    path can make torch, scipy and venv python fail to load native DLLs.
    Restore the host interpreter's DLL directory only around child creation.
    """
    import subprocess
    import sys
    if os.name == 'nt' and getattr(sys, 'frozen', False):
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.SetDllDirectoryW(None)
        try:
            return subprocess.Popen(args, **kwargs)
        finally:
            kernel.SetDllDirectoryW(str(sys._MEIPASS))
    return subprocess.Popen(args, **kwargs)
