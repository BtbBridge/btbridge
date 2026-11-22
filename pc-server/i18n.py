"""Windows PC uygulaması için Türkçe / İngilizce yerelleştirme ve dil tercihi kalıcılığı."""

from __future__ import annotations

import locale
from typing import Any

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore[assignment]

SUPPORTED_LANGUAGES: tuple[str, str] = ("tr", "en")
_REG_SUBKEY = r"Software\BTBridge"
_REG_VALUE = "Language"


def _detect_system_language() -> str:
    try:
        lang_tag = (locale.getlocale()[0] or "").lower()
        if not lang_tag:
            lang_tag = (locale.getdefaultlocale()[0] or "").lower()  # type: ignore[deprecated]
        if lang_tag.startswith("tr") or "turkish" in lang_tag:
            return "tr"
    except Exception:
        pass
    return "tr" if _is_turkish_windows_ui() else "en"


def _is_turkish_windows_ui() -> bool:
    try:
        import ctypes

        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # 0x1F = LANG_TURKISH
        return (lang_id & 0xFF) == 0x1F
    except Exception:
        return True


def load_language() -> tuple[str, bool]:
    """Kayıt defterinden tercih edilen dili yükler: (dil_kodu, kayitli_mi)."""
    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, _REG_VALUE)
                if isinstance(val, str):
                    normalized = val.strip().lower()
                    if normalized in SUPPORTED_LANGUAGES:
                        return normalized, True
        except OSError:
            pass
    return _detect_system_language(), False


def save_language(lang: str) -> None:
    """Seçilen dili Windows kayıt defterine kaydeder."""
    normalized = lang.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES or winreg is None:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY) as key:
            winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, normalized)
    except OSError:
        pass


STRINGS: dict[str, dict[str, str]] = {
    "tr": {
        "window_title": "BTBridge — USB & Wi-Fi Ses Köprüsü",
        "app_subtitle": "Windows Sistem Sesini Sıfıra Yakın Gecikmeyle Android'e Aktar",
        "status_ready": "● Hazır",
        "status_waiting": "● Bağlantı Bekleniyor",
        "status_connected": "● Bağlı",
        "card_latency": "Gecikme (RTT)",
        "card_bitrate": "Veri Hızı",
        "card_client": "Bağlı Cihaz",
        "waiting": "Bekleniyor",
        "stopped": "Durduruldu",
        "connected": "Bağlı",
        "measuring": "Ölçülüyor...",
        "source_title": "WASAPI Loopback Ses Kaynağı",
        "searching_devices": "Cihaz aranıyor...",
        "no_device_found": "Aktif WASAPI çıkış cihazı bulunamadı",
        "refresh": "Yenile",
        "mute_switch": "Yayın sırasında PC kulaklığını/hoparlörünü sustur",
        "mute_preparing": "Ses yönlendirme hazırlanıyor...",
        "mute_off": "Kapalı: Ses hem PC çıkışından hem Bluetooth kulaklıktan çalar.",
        "mute_default": "Yayın başlarken ses sessiz/sanal çıkışa yönlendirilir.",
        "mute_route_sink": "Sessiz çıkışa aktarılıyor: {name} (Windows sesi açık kalır)",
        "mute_zero_vol": "Donanım ses sıfırlama hazır • Durdurulunca eski ses seviyesi geri döner.",
        "mute_hw_fallback": "Sessiz/sanal çıkış bulunamadı • Donanım susturma kullanılacak.",
        "mute_none": "Uyarı: Bu cihaz için sessiz çıkış veya susturma yöntemi bulunamadı.",
        "mode_title": "Bağlantı Modu",
        "mode_usb": "USB (ADB Reverse)",
        "mode_wifi": "Yerel Wi-Fi",
        "adb_checking": "ADB kontrol ediliyor...",
        "adb_missing": "ADB bulunamadı (Kurulum eksik)",
        "adb_ready": "ADB hazır: {name}",
        "btn_install_apk": "Telefona APK Kur",
        "btn_installing": "Kuruluyor...",
        "btn_usb_bridge": "USB Köprüsünü Başlat",
        "btn_usb_setting_up": "Kuruluyor...",
        "wifi_info": "Wi-Fi Modu: ADPCM + UDP FEC aktif • IP: {ips} (Port: {port})",
        "no_local_ip": "Yerel IP bulunamadı",
        "btn_start": "Yayını Başlat",
        "btn_starting": "Başlatılıyor...",
        "btn_stop": "Yayını Durdur",
        "vu_title": "Canlı Ses Seviyesi (48 kHz Stereo PCM)",
        "log_title": "Sistem Günlüğü",
        "log_devices_err": "Ses cihazları listelenemedi: {err}",
        "log_devices_count": "{count} adet WASAPI Loopback ses cihazı bulundu.",
        "log_adb_missing": "Uyarı: adb.exe bulunamadı. USB modu için ADB gereklidir.",
        "log_adb_detected": "ADB algılandı: {path}",
        "log_select_valid": "Hata: Lütfen geçerli bir WASAPI Loopback ses cihazı seçin.",
        "log_start_failed": "Yayın başlatılamadı: {err}",
        "log_routed_silent": "Windows sesi açık tutuldu, ses sessiz çıkışa aktarıldı: {name}",
        "log_zero_vol": "PC ses seviyesi sıfırlandı: {name}",
        "log_hw_mute": "PC çıkışı susturuldu (donanım mute): {name}",
        "log_silence_failed": "Uyarı: PC çıkışı susturulamadı, ses her iki cihazdan da çalabilir.",
        "log_silence_err": "PC susturma uygulanamadı: {err}",
        "log_restored": "PC kulaklığı/ses çıkışı eski durumuna döndürüldü.",
        "log_stopped": "Yayın durduruldu.",
        "log_usb_repaired": "USB köprüsü otomatik yenilendi: {msg}",
        "log_tray_err": "Sistem tepsisi başlatılamadı: {err}",
        "tray_show": "BTBridge'i Göster",
        "tray_stop": "Yayını Durdur",
        "tray_start": "Yayını Başlat",
        "tray_quit": "Tamamen Çık",
        "tray_minimized": "BTBridge arka planda çalışmaya devam ediyor.",
        "tray_tooltip_default": "BTBridge — Ses Köprüsü",
        "tray_tooltip_ready": "BTBridge — Hazır",
        "tray_tooltip_waiting": "BTBridge — Bağlantı Bekleniyor",
    },
    "en": {
        "window_title": "BTBridge — USB & Wi-Fi Audio Bridge",
        "app_subtitle": "Stream Windows System Audio to Android with Near-Zero Latency",
        "status_ready": "● Ready",
        "status_waiting": "● Waiting for Connection",
        "status_connected": "● Connected",
        "card_latency": "Latency (RTT)",
        "card_bitrate": "Bitrate",
        "card_client": "Connected Device",
        "waiting": "Waiting",
        "stopped": "Stopped",
        "connected": "Connected",
        "measuring": "Measuring...",
        "source_title": "WASAPI Loopback Audio Source",
        "searching_devices": "Searching devices...",
        "no_device_found": "No active WASAPI output device found",
        "refresh": "Refresh",
        "mute_switch": "Mute PC speakers/headphones while streaming",
        "mute_preparing": "Preparing audio routing...",
        "mute_off": "Off: Audio plays through both PC output and Bluetooth headphones.",
        "mute_default": "Audio will be routed to a silent/virtual output when streaming starts.",
        "mute_route_sink": "Routing to silent sink: {name} (Windows audio stays active)",
        "mute_zero_vol": "Hardware zero-volume ready • Restores previous level on stop.",
        "mute_hw_fallback": "No silent sink found • Hardware mute will be used.",
        "mute_none": "Warning: No silent sink or mute method available for this device.",
        "mode_title": "Connection Mode",
        "mode_usb": "USB (ADB Reverse)",
        "mode_wifi": "Local Wi-Fi",
        "adb_checking": "Checking ADB...",
        "adb_missing": "ADB not found (Installation incomplete)",
        "adb_ready": "ADB ready: {name}",
        "btn_install_apk": "Install APK to Phone",
        "btn_installing": "Installing...",
        "btn_usb_bridge": "Start USB Bridge",
        "btn_usb_setting_up": "Setting up...",
        "wifi_info": "Wi-Fi Mode: ADPCM + UDP FEC active • IP: {ips} (Port: {port})",
        "no_local_ip": "No local IP found",
        "btn_start": "Start Streaming",
        "btn_starting": "Starting...",
        "btn_stop": "Stop Streaming",
        "vu_title": "Live Audio Level (48 kHz Stereo PCM)",
        "log_title": "System Log",
        "log_devices_err": "Failed to list audio devices: {err}",
        "log_devices_count": "Found {count} WASAPI Loopback audio device(s).",
        "log_adb_missing": "Warning: adb.exe not found. ADB is required for USB mode.",
        "log_adb_detected": "ADB detected: {path}",
        "log_select_valid": "Error: Please select a valid WASAPI Loopback audio device.",
        "log_start_failed": "Failed to start stream: {err}",
        "log_routed_silent": "Windows audio kept active, routed output to silent sink: {name}",
        "log_zero_vol": "PC volume set to zero: {name}",
        "log_hw_mute": "PC output muted (hardware mute): {name}",
        "log_silence_failed": "Warning: Could not silence PC output; audio may play on both devices.",
        "log_silence_err": "Failed to silence PC output: {err}",
        "log_restored": "PC speakers/audio output restored to previous state.",
        "log_stopped": "Streaming stopped.",
        "log_usb_repaired": "USB bridge auto-repaired: {msg}",
        "log_tray_err": "Failed to start system tray: {err}",
        "tray_show": "Show BTBridge",
        "tray_stop": "Stop Streaming",
        "tray_start": "Start Streaming",
        "tray_quit": "Quit Completely",
        "tray_minimized": "BTBridge continues running in the background.",
        "tray_tooltip_default": "BTBridge — Audio Bridge",
        "tray_tooltip_ready": "BTBridge — Ready",
        "tray_tooltip_waiting": "BTBridge — Waiting for Connection",
    },
}


def tr(lang: str, key: str, **kwargs: Any) -> str:
    """Belirtilen dil için çeviri metnini döndürür; yoksa Türkçe veya anahtar adını kullanır."""
    table = STRINGS.get(lang, STRINGS["tr"])
    template = table.get(key) or STRINGS["tr"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
