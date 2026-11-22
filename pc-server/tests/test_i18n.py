"""Windows PC uygulaması TR/EN i18n modülü birim testleri."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

import i18n  # noqa: E402


def test_tr_and_en_have_identical_keys() -> None:
    tr_keys = set(i18n.STRINGS["tr"].keys())
    en_keys = set(i18n.STRINGS["en"].keys())
    assert tr_keys == en_keys
    assert len(tr_keys) > 20


def test_tr_formatting_and_fallback() -> None:
    assert i18n.tr("en", "btn_start") == "Start Streaming"
    assert i18n.tr("tr", "btn_start") == "Yayını Başlat"
    assert "50005" in i18n.tr("en", "wifi_info", ips="192.168.1.5", port=50005)
    assert i18n.tr("xx", "btn_start") == "Yayını Başlat"
    assert i18n.tr("en", "nonexistent_key") == "nonexistent_key"


def test_load_language_falls_back_when_registry_missing() -> None:
    with (
        patch.object(i18n, "winreg", None),
        patch.object(i18n, "_detect_system_language", return_value="en"),
    ):
        lang, saved = i18n.load_language()
        assert lang == "en"
        assert saved is False
