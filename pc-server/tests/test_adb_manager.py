"""ADB bulma, APK keşfi ve tek tıkla APK kurulum birim testleri."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

import adb_manager  # noqa: E402


def test_find_adb_prefers_installed_platform_tools_when_frozen(tmp_path: Path) -> None:
    fake_exe = tmp_path / "BTBridge.exe"
    fake_exe.write_bytes(b"")
    pt_adb = tmp_path / "platform-tools" / "adb.exe"
    pt_adb.parent.mkdir(parents=True)
    pt_adb.write_bytes(b"")

    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "executable", str(fake_exe)),
    ):
        found = adb_manager.find_adb()
    assert found == pt_adb


def test_find_apk_detects_root_and_frozen_apk(tmp_path: Path) -> None:
    apk = tmp_path / "BTBridge.apk"
    apk.write_bytes(b"apk")
    assert adb_manager.find_apk(project_root=tmp_path) == apk

    fake_exe = tmp_path / "BTBridge.exe"
    fake_exe.write_bytes(b"")
    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "executable", str(fake_exe)),
    ):
        assert adb_manager.find_apk() == apk


def test_install_apk_success_and_user0_fallback(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    apk = tmp_path / "BTBridge.apk"
    adb.write_bytes(b"")
    apk.write_bytes(b"")

    calls: list[list[str]] = []

    def fake_run(args, adb_path=None, timeout=10.0):
        calls.append(args)
        if args[:2] == ["-s", "SER1"] and args[2] == "install" and "--user" not in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="SecurityException: user 150")
        return subprocess.CompletedProcess(args, 0, stdout="Success", stderr="")

    with (
        patch.object(adb_manager, "list_devices", return_value=[("SER1", "device")]),
        patch.object(adb_manager, "run_adb", side_effect=fake_run),
    ):
        ok, msg = adb_manager.install_apk(apk_path=apk, adb_path=adb)

    assert ok is True
    assert "SER1" in msg
    assert any("--user" in c for c in calls)
    assert any("am" in c and "start" in c for c in calls)


def test_install_apk_handles_unauthorized_and_missing_device(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    apk = tmp_path / "BTBridge.apk"
    adb.write_bytes(b"")
    apk.write_bytes(b"")

    with patch.object(adb_manager, "list_devices", return_value=[("SER1", "unauthorized")]):
        ok, msg = adb_manager.install_apk(apk_path=apk, adb_path=adb)
    assert ok is False
    assert "onay" in msg.lower()

    with patch.object(adb_manager, "list_devices", return_value=[]):
        ok2, msg2 = adb_manager.install_apk(apk_path=apk, adb_path=adb)
    assert ok2 is False
    assert "cihaz bulunamadı" in msg2.lower()
