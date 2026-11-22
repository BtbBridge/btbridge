"""Windows Core Audio kontrol ve PC susturma testleri."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

import audio_control as ac  # noqa: E402


def test_list_render_endpoints_detects_default() -> None:
    endpoints = ac.list_render_endpoints()
    assert len(endpoints) >= 1
    assert any(ep.is_default for ep in endpoints)
    default_id = ac.get_default_render_endpoint_id()
    assert default_id is not None
    assert any(ep.device_id == default_id for ep in endpoints)


def test_find_endpoint_for_loopback_name_matches_suffix() -> None:
    fake_eps = [
        ac.RenderEndpoint("id-usb", "Hoparlör (USB PnP Audio Device)", True, True, True),
        ac.RenderEndpoint("id-mon", "LS27DG30X (NVIDIA High Definition Audio)", False, True, False),
    ]
    matched = ac.find_endpoint_for_loopback_name(
        "Hoparlör (USB PnP Audio Device) [Loopback]",
        endpoints=fake_eps,
    )
    assert matched is not None
    assert matched.device_id == "id-usb"


def test_find_silent_sink_endpoint_prefers_monitor_over_default() -> None:
    fake_eps = [
        ac.RenderEndpoint("id-usb", "Hoparlör (USB PnP Audio Device)", True, True, True),
        ac.RenderEndpoint("id-mon", "LS27DG30X (NVIDIA High Definition Audio)", False, True, False),
    ]
    sink = ac.find_silent_sink_endpoint(exclude_id="id-usb", endpoints=fake_eps)
    assert sink is not None
    assert sink.device_id == "id-mon"


def test_silencer_hardware_mute_and_idempotent_restore() -> None:
    silencer = ac.LocalAudioSilencer()
    with (
        patch.object(ac, "get_endpoint_mute", return_value=False),
        patch.object(ac, "set_endpoint_mute", return_value=True) as mock_set_mute,
    ):
        assert silencer.activate_hardware_mute("id-usb") is True
        assert silencer.is_active is True
        assert silencer.active_mode == "hardware_mute"
        mock_set_mute.assert_called_with("id-usb", True)

        assert silencer.restore() == "hardware_mute"
        assert silencer.is_active is False
        mock_set_mute.assert_called_with("id-usb", False)

        # İkinci restore çağrısı güvenle yoksayılmalı
        assert silencer.restore() is None


def test_silencer_silent_route_and_restore() -> None:
    silencer = ac.LocalAudioSilencer()
    with (
        patch.object(ac, "get_default_render_endpoint_id", return_value="id-usb"),
        patch.object(ac, "set_default_render_endpoint", return_value=True) as mock_set_def,
    ):
        assert silencer.activate_silent_route("id-mon") is True
        assert silencer.active_mode == "route_silent"
        mock_set_def.assert_called_with("id-mon")

        assert silencer.restore() == "route_silent"
        mock_set_def.assert_called_with("id-usb")
        assert silencer.restore() is None
