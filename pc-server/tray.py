"""Windows sistem tepsisi (system tray) simgesi ve menü denetleyicisi."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray
from pystray import Menu, MenuItem


def _load_tray_image() -> Image.Image:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "btbridge.ico")
    candidates.append(Path(__file__).resolve().parent / "btbridge.ico")

    for path in candidates:
        if path.is_file():
            try:
                with Image.open(path) as img:
                    return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

    # Fallback: koyu lacivert arka plan üzerine zümrüt yeşili ekolayzır simgesi
    img = Image.new("RGBA", (64, 64), (11, 17, 32, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(22, 32, 50, 255))
    bars = [(16, 24, 20, 40), (24, 18, 28, 46), (32, 13, 36, 51), (40, 20, 44, 44), (48, 26, 52, 38)]
    for x0, y0, x1, y1 in bars:
        draw.rectangle((x0, y0, x1, y1), fill=(16, 185, 129, 255))
    return img


class TrayController:
    """Pencere kapatıldığında arka planda çalışan sistem tepsisi yöneticisi."""

    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle_stream: Callable[[], None],
        on_quit: Callable[[], None],
        is_streaming: Callable[[], bool],
    ) -> None:
        self._on_show = on_show
        self._on_toggle_stream = on_toggle_stream
        self._on_quit = on_quit
        self._is_streaming = is_streaming
        self._icon: Optional[pystray.Icon] = None
        self._notified_once = False

    def start(self) -> None:
        if self._icon is not None:
            return
        image = _load_tray_image()
        menu = Menu(
            MenuItem("BTBridge'i Göster", lambda _icon, _item: self._on_show(), default=True),
            MenuItem(
                lambda _item: "Yayını Durdur" if self._is_streaming() else "Yayını Başlat",
                lambda _icon, _item: self._on_toggle_stream(),
            ),
            Menu.SEPARATOR,
            MenuItem("Tamamen Çık", lambda _icon, _item: self._on_quit()),
        )
        self._icon = pystray.Icon("BTBridge", image, "BTBridge — Ses Köprüsü", menu)
        self._icon.run_detached()

    def notify_minimized(self) -> None:
        if self._icon is None or self._notified_once:
            return
        self._notified_once = True
        try:
            self._icon.notify("BTBridge arka planda çalışmaya devam ediyor.", "BTBridge")
        except Exception:
            pass

    def update_tooltip(self, text: str) -> None:
        if self._icon is None:
            return
        try:
            self._icon.title = text[:127]
        except Exception:
            pass

    def stop(self) -> None:
        icon = self._icon
        self._icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
