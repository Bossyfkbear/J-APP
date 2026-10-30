"""Install only requested offline audio modules in a separate Python 3.11 venv.

No install or download occurs during app startup. --list is read-only.
The Windows .bat wrapper is the explicit user entrypoint.
"""
from __future__ import annotations

import argparse
from importlib.util import find_spec
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("denoise", "split", "meter", "pitch", "dereverb")
MODEL_FOR = {"denoise": "DeepFilterNet3", "split": "Demucs", "meter": "BeatThis"}
PACKAGE_FOR = {
    "denoise": ("torch", "torchaudio", "df"),
    "split": ("torch", "torchaudio", "demucs"),
    "meter": ("torch", "torchaudio", "beat_this"),
    "pitch": ("librosa",),
    "dereverb": ("scipy", "nara_wpe"),
}


def plan(module: str, *, with_models: bool = False, root: Path = ROOT) -> dict:
    """Pure install plan, suitable for tests; never contacts the network."""
    if module != "all" and module not in MODULES:
        raise ValueError("Unknown optional module: " + module)
    selected = MODULES if module == "all" else (module,)
    req = (root / "requirements-ai-windows.txt" if module == "all" else
           root / "requirements-ai-modules" / (module + ".txt"))
    models = tuple(MODEL_FOR[item] for item in selected if item in MODEL_FOR) if with_models else ()
    return {"modules": list(selected), "requirements": str(req),
            "models": list(models), "venv": str(root / ".apt-ai"),
            "network_required": True}


def venv_python(folder: Path) -> Path:
    return folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run_command(args):
    print("+", " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], check=True, cwd=ROOT)


def prepare(module: str, *, with_models: bool = False) -> None:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 11) or platform.architecture()[0] != "64bit":
        raise RuntimeError("Optional Windows modules require Windows, Python 3.11 x64.")
    spec = plan(module, with_models=with_models)
    env = ROOT / ".apt-ai"
    interpreter = venv_python(env)
    if not interpreter.is_file():
        run_command((sys.executable, "-m", "venv", str(env)))
    run_command((interpreter, "-c",
                 "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"))
    req = Path(spec["requirements"])
    if not req.is_file():
        raise FileNotFoundError("Missing optional requirements file: " + str(req))
    run_command((interpreter, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req),
                 "-r", str(ROOT / "requirements.txt")))
    # Check only this module's imports: other optional modules need not be installed.
    package_names = sorted({name for item in spec["modules"] for name in PACKAGE_FOR[item]})
    probe = ("import importlib.util,sys; missing=[n for n in sys.argv[1:] "
             "if importlib.util.find_spec(n) is None]; "
             "print('Missing packages:',missing) if missing else print('Module packages detected'); "
             "sys.exit(bool(missing))")
    run_command((interpreter, "-c", probe, *package_names))
    run_command((interpreter, "-m", "pip", "check"))
    if with_models:
        for name in spec["models"]:
            run_command((interpreter, str(ROOT / "scripts" / "download_models.py"),
                         "--directory", str(ROOT / "models"), "--model", name))
    print("Selected optional modules installed:", ", ".join(spec["modules"]))
    print("For neural inference, select the locally installed model in Audio Post Toolkit.")
    print("The main desktop EXE and its core features remain independent.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicit Windows setup of independent optional audio modules")
    parser.add_argument("--module", choices=("all", *MODULES), default="all",
                        help="Only install one module (denoise/split/meter/pitch/dereverb). "
                             "Default all preserves previous setup behavior.")
    parser.add_argument("--with-models", action="store_true",
                        help="Explicitly download SHA256-pinned official models only for selected neural modules.")
    parser.add_argument("--list", action="store_true", help="List modules and packages without installing anything.")
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps({"modules": list(MODULES), "model_for": MODEL_FOR,
                          "examples": ["setup_ai_windows.bat --module denoise --with-models",
                                       "setup_ai_windows.bat --module split --with-models",
                                       "setup_ai_windows.bat --module pitch"]}, indent=2))
        return 0
    try:
        prepare(args.module, with_models=args.with_models)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("Optional module setup failed:", str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
