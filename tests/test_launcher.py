from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PS_LAUNCHER = PROJECT_ROOT / "start-windows.ps1"
BAT_LAUNCHER = PROJECT_ROOT / "start-windows.bat"
CHINESE_BAT_WRAPPER = PROJECT_ROOT / "\u542f\u52a8-Windows.bat"
APP_FILE = PROJECT_ROOT / "app.py"


def assert_cmd_safe_batch(path: Path):
    raw = path.read_bytes()

    assert all(byte < 128 for byte in raw)
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_ascii_windows_powershell_launcher_exists():
    assert PS_LAUNCHER.exists()


def test_ascii_windows_batch_launcher_exists():
    assert BAT_LAUNCHER.exists()


def test_chinese_named_batch_wrapper_exists_for_double_clicking():
    assert CHINESE_BAT_WRAPPER.exists()


def test_batch_launchers_are_cmd_safe_ascii_with_crlf_line_endings():
    assert_cmd_safe_batch(BAT_LAUNCHER)
    assert_cmd_safe_batch(CHINESE_BAT_WRAPPER)


def test_powershell_launcher_uses_project_virtual_environment_python():
    script = PS_LAUNCHER.read_text(encoding="utf-8")

    assert "$PythonBin = Join-Path $ProjectDir '.venv\\Scripts\\python.exe'" in script
    assert "Start-Process -FilePath $PythonBin" in script


def test_powershell_launcher_finds_or_reuses_local_port():
    script = PS_LAUNCHER.read_text(encoding="utf-8")

    assert "function Find-RunningAppUrl" in script
    assert "function Find-AvailablePort" in script
    assert "5000..5010" in script
    assert "$env:VOCABULARY_PORT = [string]$AppPort" in script


def test_powershell_launcher_waits_and_opens_browser():
    script = PS_LAUNCHER.read_text(encoding="utf-8")

    assert "function Wait-ForApp" in script
    assert "Start-Process $AppUrl" in script
    assert "Vocabulary did not become ready" in script


def test_batch_launcher_bypasses_policy_for_this_process_only():
    script = BAT_LAUNCHER.read_text(encoding="ascii")

    assert "powershell.exe" in script
    assert "-ExecutionPolicy Bypass" in script
    assert "-File" in script
    assert "start-windows.ps1" in script


def test_chinese_named_batch_wrapper_delegates_to_ascii_batch_file():
    script = CHINESE_BAT_WRAPPER.read_text(encoding="ascii")

    assert "start-windows.bat" in script
    assert "\u542f\u52a8" not in script


def test_app_reads_port_from_environment_for_launcher():
    app_source = APP_FILE.read_text(encoding="utf-8")

    assert "import os" in app_source
    assert 'port=int(os.environ.get("VOCABULARY_PORT", "5000"))' in app_source
