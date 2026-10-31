"""Model directory auto-discovery and secure explicit installer args."""
from pathlib import Path
import pytest
from aptk.ai_control import installed_model_dir, install_command, MODELS


@pytest.mark.parametrize('operation,name', list(MODELS.items()))
def test_installed_model_is_selected_automatically(tmp_path,operation,name):
    model=tmp_path/'models'/name
    model.mkdir(parents=True)
    assert installed_model_dir(operation,root=tmp_path)==str(model.resolve())
    assert installed_model_dir(operation,'',root=tmp_path)==str(model.resolve())


def test_explicit_model_path_wins(tmp_path):
    existing=tmp_path/'models'/'DeepFilterNet3'
    existing.mkdir(parents=True)
    custom=tmp_path/'recording_session_model'
    custom.mkdir()
    assert installed_model_dir('denoise',str(custom),root=tmp_path)==str(custom.resolve())
    assert installed_model_dir('pitch',root=tmp_path) is None
    assert installed_model_dir('meter',root=tmp_path) is None


@pytest.mark.parametrize('module,model', [('denoise',True),('split',True),('meter',True),
                                         ('pitch',False),('dereverb',False)])
def test_installer_only_selects_requested_module(tmp_path,module,model):
    (tmp_path/'setup_ai_windows.bat').write_bytes(b'@echo off\\r\\n')
    argv=install_command(tmp_path,module,download_models=model,platform='nt')
    assert argv[:3]==['cmd.exe','/d','/c']
    assert argv[4:]==(['--module',module,'--with-models'] if model else ['--module',module])


def test_installer_rejects_unknown_and_spurious_downloads(tmp_path):
    (tmp_path/'setup_ai_windows.bat').write_text('echo test')
    with pytest.raises(ValueError):
        install_command(tmp_path,';del *',platform='nt')
    with pytest.raises(ValueError):
        install_command(tmp_path,'pitch',download_models=True,platform='nt')
    with pytest.raises(RuntimeError):
        install_command(tmp_path,'denoise',platform='posix')
    with pytest.raises(FileNotFoundError):
        install_command(tmp_path/'missing','denoise',platform='nt')


def test_external_process_launches_without_mutating_parent():
    import sys
    from aptk.ai_control import external_popen
    import subprocess
    proc=external_popen(
        [sys.executable,'-c','import sys;print(sys.version_info.major)'],
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    data,err=proc.communicate(timeout=10)
    assert proc.returncode==0,err
    assert data.strip()==b'3'
