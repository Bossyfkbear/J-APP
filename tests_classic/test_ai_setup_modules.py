"""Offline-only setup contract: selecting one tool never installs all AI models."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "setup_ai_modules.py"
DOWNLOAD = REPO / "scripts" / "download_models.py"


def _module():
    spec = importlib.util.spec_from_file_location("apt_setup_mod", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_install_plans_are_independent():
    module = _module()
    for selected in module.MODULES:
        result = module.plan(selected, with_models=True)
        assert result["modules"] == [selected]
        assert Path(result["requirements"]).is_file()
        expected = [module.MODEL_FOR[selected]] if selected in module.MODEL_FOR else []
        assert result["models"] == expected
    assert set(module.plan("all", with_models=True)["models"]) == set(module.MODEL_FOR.values())


def test_list_command_never_installs_packages():
    response = subprocess.run([sys.executable, str(SCRIPT), "--list"],
                              capture_output=True, text=True, check=True)
    data = json.loads(response.stdout)
    assert len(data["modules"]) == 5
    assert "denoise" in data["modules"]


def test_official_downloader_supports_selective_models():
    script = DOWNLOAD.read_text(encoding="utf-8")
    assert "parser.add_argument('--model'" in script
    assert "args.model or MODELS" in script
    for name in ("DeepFilterNet3", "Demucs", "BeatThis"):
        assert name in script


def test_staged_requirements_use_pinned_packages():
    folder = REPO / "requirements-ai-modules"
    for name in ("denoise", "split", "meter", "pitch", "dereverb"):
        content = (folder / (name + ".txt")).read_text()
        assert "==" in content or "-r common.txt" in content
    common = (folder / "common.txt").read_text()
    assert "torch==2.5.1+cpu" in common
    assert "torchaudio==2.5.1+cpu" in common
