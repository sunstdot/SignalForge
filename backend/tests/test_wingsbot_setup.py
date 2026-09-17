import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = PROJECT_ROOT / "scripts" / "setup-wingsbot.zsh"


def test_setup_uses_selected_interpreter_and_prepares_editable_wingsbot(tmp_path):
    project = tmp_path / "signalforge"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / SETUP_SCRIPT.name
    shutil.copy2(SETUP_SCRIPT, script)

    source = tmp_path / "wingsbot-source"
    invoke_package = source / "wingsbot" / "invoke"
    invoke_package.mkdir(parents=True)
    (source / "wingsbot" / "__init__.py").write_text(
        "__version__ = 'test-version'\n", encoding="utf-8"
    )
    (invoke_package / "__init__.py").write_text(
        "class WingsbotClient:\n    pass\n", encoding="utf-8"
    )

    calls = tmp_path / "python-calls"
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_PYTHON_CALLS\"\n"
        "if [ \"$1 $2\" = '-m pip' ]; then exit 0; fi\n"
        "exec \"$REAL_PYTHON\" \"$@\"\n",
        encoding="utf-8",
    )
    dist_info = source / "ks_wingsbot-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: ks-wingsbot\nVersion: 1.2.3\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = {
        **os.environ,
        "SIGNALFORGE_PYTHON": str(fake_python),
        "WINGSBOT_SOURCE": str(source),
        "FAKE_PYTHON_CALLS": str(calls),
        "REAL_PYTHON": shutil.which("python3") or "python3",
        "PYTHONPATH": str(source),
    }

    completed = subprocess.run(
        ["zsh", str(script)],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    recorded = calls.read_text(encoding="utf-8").splitlines()
    assert recorded[0].startswith(
        "-m pip wheel --no-build-isolation --no-deps --wheel-dir "
    )
    assert recorded[0].endswith(f" {source}")
    assert recorded[1:] == [
        "-m pip uninstall -y wingsbot-ai ks-wingsbot",
        f"-m pip install --no-build-isolation -e {source}",
        "-",
    ]
    assert (project / ".wingsbot" / "workspace").is_dir()
    assert "WingsbotClient import OK" in completed.stdout


def test_setup_script_has_valid_zsh_syntax():
    completed = subprocess.run(
        ["zsh", "-n", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_setup_does_not_uninstall_when_editable_install_preparation_fails(tmp_path):
    project = tmp_path / "signalforge"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / SETUP_SCRIPT.name
    shutil.copy2(SETUP_SCRIPT, script)
    source = tmp_path / "broken-wingsbot-source"
    source.mkdir()
    calls = tmp_path / "python-calls"
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_PYTHON_CALLS\"\n"
        "case \"$*\" in\n"
        "  *pip\\ wheel*) exit 1 ;;\n"
        "  *pip\\ uninstall*) exit 99 ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = {
        **os.environ,
        "SIGNALFORGE_PYTHON": str(fake_python),
        "WINGSBOT_SOURCE": str(source),
        "FAKE_PYTHON_CALLS": str(calls),
    }

    completed = subprocess.run(
        ["zsh", str(script)],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    recorded = calls.read_text(encoding="utf-8")
    assert completed.returncode != 0
    assert "pip wheel" in recorded
    assert "pip uninstall" not in recorded
