"""Windows için otomatik ADB bulma ve `adb reverse` USB köprü yöneticisi."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional

from protocol import DEFAULT_PORT


def _default_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _extract_bundled_adb() -> Optional[Path]:
    """PyInstaller tek dosya içindeki gömülü adb.exe ve DLL'leri kalıcı kullanıcı klasörüne çıkarır."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    bundled_dir = Path(meipass) / "adb"
    bundled_adb = bundled_dir / "adb.exe"
    if not bundled_adb.is_file():
        return None

    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    target_dir = Path(local_app_data) / "BTBridge" / "platform-tools"
    target_dir.mkdir(parents=True, exist_ok=True)

    for fname in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"):
        src = bundled_dir / fname
        dst = target_dir / fname
        if not src.is_file():
            continue
        if not dst.is_file() or dst.stat().st_size != src.stat().st_size:
            try:
                shutil.copy2(src, dst)
            except OSError:
                # adb.exe arka planda zaten çalışıyorsa ve mevcut kopya duruyorsa onu kullan
                if not dst.is_file():
                    return None

    target_adb = target_dir / "adb.exe"
    return target_adb if target_adb.is_file() else None


def find_adb(project_root: Optional[Path] = None) -> Optional[Path]:
    """Önce .tools SDK, frozen ise gömülü ADB, sonra ortam değişkenleri ve PATH içinde adb.exe arar."""
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "platform-tools" / "adb.exe")
        candidates.append(exe_dir / ".tools" / "android-sdk" / "platform-tools" / "adb.exe")

        # Taşınabilir exe senaryosunda yerel SDK yoksa gömülü ADB'yi çıkarıp kullan
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        bundled = _extract_bundled_adb()
        if bundled is not None:
            return bundled

    root = project_root or _default_project_root()
    candidates.extend(
        [
            root / ".tools" / "android-sdk" / "platform-tools" / "adb.exe",
            root / ".tools" / "android-sdk" / "platform-tools" / "adb",
        ]
    )

    for env_key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        env_val = os.environ.get(env_key)
        if env_val:
            candidates.append(Path(env_val) / "platform-tools" / "adb.exe")
            candidates.append(Path(env_val) / "platform-tools" / "adb")

    which_adb = shutil.which("adb")
    if which_adb:
        candidates.append(Path(which_adb))

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_adb(args: list[str], adb_path: Optional[Path] = None, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    """ADB komutunu arka plan penceresi açmadan çalıştırır."""
    resolved = adb_path or find_adb()
    if resolved is None:
        raise FileNotFoundError("adb.exe bulunamadı")

    kwargs: dict[str, object] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    return subprocess.run([str(resolved), *args], **kwargs)  # type: ignore[arg-type]


def list_devices(adb_path: Optional[Path] = None) -> list[tuple[str, str]]:
    """Bağlı ADB cihazlarını (serial, durum) listesi olarak döndürür."""
    proc = run_adb(["devices"], adb_path=adb_path)
    devices: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices"):
            continue
        parts = stripped.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


def setup_reverse(port: int = DEFAULT_PORT, adb_path: Optional[Path] = None) -> tuple[bool, str]:
    """USB üzerinden `adb reverse tcp:<port> tcp:<port>` tünelini kurar."""
    resolved = adb_path or find_adb()
    if resolved is None:
        return False, "ADB bulunamadı (.tools/android-sdk veya sistem PATH içinde yok)."

    try:
        devices = list_devices(adb_path=resolved)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"ADB cihaz listesi alınamadı: {exc}"

    authorized = [serial for serial, state in devices if state == "device"]
    if not authorized:
        unauthorized = [serial for serial, state in devices if state == "unauthorized"]
        if unauthorized:
            return (
                False,
                "Telefon USB hata ayıklama onayı bekliyor. Ekrandaki 'USB hata ayıklamaya izin ver' uyarısını onaylayın.",
            )
        return (
            False,
            "USB ile bağlı ve yetkili Android cihaz bulunamadı. USB Hata Ayıklama (USB Debugging) açık mı?",
        )

    try:
        proc = run_adb(
            ["-s", authorized[0], "reverse", f"tcp:{port}", f"tcp:{port}"],
            adb_path=resolved,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"adb reverse komutu başarısız: {exc}"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        return False, f"adb reverse hatası: {err or 'Bilinmeyen hata'}"

    return True, f"USB köprüsü hazır ({authorized[0]} • tcp:{port} -> tcp:{port})"


def is_reverse_active(port: int = DEFAULT_PORT, adb_path: Optional[Path] = None) -> bool:
    """Belirtilen port için aktif bir `adb reverse` tüneli olup olmadığını kontrol eder."""
    resolved = adb_path or find_adb()
    if resolved is None:
        return False
    try:
        proc = run_adb(["reverse", "--list"], adb_path=resolved, timeout=4.0)
        return proc.returncode == 0 and f"tcp:{port}" in proc.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def remove_reverse(port: int = DEFAULT_PORT, adb_path: Optional[Path] = None) -> None:
    """Kurulu `adb reverse` tünelini güvenli biçimde kaldırır."""
    resolved = adb_path or find_adb()
    if resolved is None:
        return
    try:
        run_adb(["reverse", "--remove", f"tcp:{port}"], adb_path=resolved, timeout=5.0)
    except (OSError, subprocess.SubprocessError):
        pass


def find_apk(project_root: Optional[Path] = None) -> Optional[Path]:
    """Kurulum dizininde, frozen pakette veya proje kökünde BTBridge.apk dosyasını arar."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "BTBridge.apk")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "BTBridge.apk")
    root = project_root or _default_project_root()
    candidates.append(root / "BTBridge.apk")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def install_apk(
    apk_path: Optional[Path] = None,
    adb_path: Optional[Path] = None,
) -> tuple[bool, str]:
    """BTBridge.apk dosyasını USB ile bağlı yetkili Android cihaza kurar ve başlatır."""
    resolved_adb = adb_path or find_adb()
    if resolved_adb is None:
        return False, "ADB bulunamadı (.tools/android-sdk veya platform-tools içinde yok)."

    resolved_apk = apk_path or find_apk()
    if resolved_apk is None or not resolved_apk.is_file():
        return False, "BTBridge.apk dosyası bulunamadı."

    try:
        devices = list_devices(adb_path=resolved_adb)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"ADB cihaz listesi alınamadı: {exc}"

    authorized = [serial for serial, state in devices if state == "device"]
    if not authorized:
        unauthorized = [serial for serial, state in devices if state == "unauthorized"]
        if unauthorized:
            return (
                False,
                "Telefon USB hata ayıklama onayı bekliyor. Ekrandaki 'USB hata ayıklamaya izin ver' uyarısını onaylayın.",
            )
        return (
            False,
            "USB ile bağlı ve yetkili Android cihaz bulunamadı. USB Hata Ayıklama (USB Debugging) açık mı?",
        )

    serial = authorized[0]
    try:
        proc = run_adb(["-s", serial, "install", "-r", str(resolved_apk)], adb_path=resolved_adb, timeout=60.0)
        if proc.returncode != 0:
            proc = run_adb(
                ["-s", serial, "install", "--user", "0", "-r", str(resolved_apk)],
                adb_path=resolved_adb,
                timeout=60.0,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"APK kurulum komutu başarısız: {exc}"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        return False, f"APK kurulumu başarısız: {err or 'Bilinmeyen hata'}"

    try:
        run_adb(
            ["-s", serial, "shell", "am", "start", "--user", "0", "-n", "com.btbridge.app/.ui.MainActivity"],
            adb_path=resolved_adb,
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError):
        pass

    return True, f"BTBridge.apk telefona kuruldu ve açıldı ({serial})!"
