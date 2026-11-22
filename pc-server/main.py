"""BTBridge Windows PC uygulaması giriş noktası."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def _run_smoke_test() -> int:
    import customtkinter  # noqa: F401
    import numpy  # noqa: F401
    from PIL import Image  # noqa: F401
    import pyaudiowpatch  # noqa: F401
    import pystray  # noqa: F401

    import adb_manager
    import audio_capture
    import audio_control
    import dsp
    import tray  # noqa: F401

    loopback_devices = audio_capture.list_loopback_devices()
    render_endpoints = audio_control.list_render_endpoints()
    adb_path = adb_manager.find_adb()
    apk_path = adb_manager.find_apk()
    adpcm_enc = dsp.StereoImaAdpcmEncoder()
    adpcm_ok = len(adpcm_enc.encode(b"\x00" * 1920)) == 486

    summary = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "loopback_count": len(loopback_devices),
        "loopback_devices": [d.name for d in loopback_devices],
        "render_endpoints": [
            {
                "name": e.friendly_name,
                "hw_mute": e.hw_mute,
                "hw_volume": e.hw_volume,
                "default": e.is_default,
            }
            for e in render_endpoints
        ],
        "silence_strategy": audio_control.DEFAULT_SILENCE_STRATEGY,
        "adpcm_ok": adpcm_ok,
        "adb_path": str(adb_path) if adb_path else None,
        "apk_path": str(apk_path) if apk_path else None,
    }
    if sys.stdout is not None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if (adpcm_ok and adb_path is not None and len(loopback_devices) > 0 and len(render_endpoints) > 0) else 1


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    if "--smoke-test" in sys.argv[1:]:
        raise SystemExit(_run_smoke_test())

    from ui import BTBridgeApp

    app = BTBridgeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
