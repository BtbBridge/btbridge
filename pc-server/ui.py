"""BTBridge Windows PC modern karanlık tema kullanıcı arayüzü."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from typing import Optional

import customtkinter as ctk

import adb_manager
from audio_capture import LoopbackDevice, WasapiLoopbackCapture, list_loopback_devices
import audio_control
from protocol import DEFAULT_PORT
from server import AudioBridgeServer, get_local_ipv4_addresses
from tray import TrayController


def _resolve_icon_path() -> Optional[Path]:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "btbridge.ico")
    candidates.append(Path(__file__).resolve().parent / "btbridge.ico")
    for path in candidates:
        if path.is_file():
            return path
    return None

BG_ROOT = "#0B1120"
BG_CARD = "#162032"
BG_PANEL = "#1E293B"
BORDER_COLOR = "#2A3950"
TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
ACCENT_EMERALD = "#10B981"
ACCENT_EMERALD_HOVER = "#059669"
ACCENT_SKY = "#38BDF8"
ACCENT_AMBER = "#F59E0B"
ACCENT_ROSE = "#F43F5E"
ACCENT_ROSE_HOVER = "#E11D48"


class StereoVuMeter(tk.Canvas):
    """Düşük maliyetli, akıcı stereo VU seviye göstergesi."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            height=52,
            bg=BG_PANEL,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            **kwargs,
        )
        self._left = 0.0
        self._right = 0.0
        self._bar_l = None
        self._bar_r = None
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_levels(self, left: float, right: float) -> None:
        self._left = max(0.0, min(1.0, left))
        self._right = max(0.0, min(1.0, right))
        self._redraw()

    def _level_color(self, level: float) -> str:
        if level > 0.85:
            return ACCENT_ROSE
        if level > 0.65:
            return ACCENT_AMBER
        return ACCENT_EMERALD

    def _redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 200)
        pad_x = 34
        bar_w = max(40, w - pad_x - 14)

        self.create_text(14, 17, text="L", fill=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w")
        self.create_text(14, 41, text="R", fill=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w")

        for y_top, val in ((10, self._left), (34, self._right)):
            self.create_rectangle(pad_x, y_top, pad_x + bar_w, y_top + 14, fill="#0F172A", outline="")
            fill_w = int(bar_w * val)
            if fill_w > 0:
                self.create_rectangle(
                    pad_x,
                    y_top,
                    pad_x + fill_w,
                    y_top + 14,
                    fill=self._level_color(val),
                    outline="",
                )


class BTBridgeApp(ctk.CTk):
    """BTBridge ana masaüstü penceresi."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("BTBridge — USB & Wi-Fi Ses Köprüsü")
        self.geometry("680x630")
        self.minsize(620, 580)
        self.configure(fg_color=BG_ROOT)

        icon_path = _resolve_icon_path()
        if icon_path is not None:
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._devices: list[LoopbackDevice] = []
        self._device_map: dict[str, LoopbackDevice] = {}
        self._endpoints: list[audio_control.RenderEndpoint] = []
        self._silencer = audio_control.LocalAudioSilencer()

        self._server: Optional[AudioBridgeServer] = None
        self._capture: Optional[WasapiLoopbackCapture] = None
        self._streaming = False

        self._vu_lock = threading.Lock()
        self._vu_left = 0.0
        self._vu_right = 0.0

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._adb_reverse_ready = False
        self._is_usb_mode = True
        self._last_reverse_check = 0.0
        self._reverse_checking = False
        self._last_tray_tooltip = ""

        self._tray = TrayController(
            on_show=lambda: self.after(0, self._restore_from_tray),
            on_toggle_stream=lambda: self.after(0, self._toggle_streaming),
            on_quit=lambda: self.after(0, self._quit_completely),
            is_streaming=lambda: self._streaming,
        )

        self._build_ui()
        self._refresh_devices()
        self._check_adb_status()

        try:
            self._tray.start()
        except Exception as exc:
            self.log(f"Sistem tepsisi başlatılamadı: {exc}")

        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.after(33, self._ui_tick)

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=12)

        # Üst Başlık & Durum Rozeti
        header = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        header.pack(fill="x", pady=(0, 8))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", padx=14, pady=10)
        ctk.CTkLabel(
            title_col,
            text="BTBridge",
            font=("Segoe UI", 21, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="Windows Sistem Sesini Sıfıra Yakın Gecikmeyle Android'e Aktar",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w")

        self._status_badge = ctk.CTkLabel(
            header,
            text="● Hazır",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MUTED,
            fg_color=BG_PANEL,
            corner_radius=12,
            padx=12,
            pady=5,
        )
        self._status_badge.pack(side="right", padx=14)

        # Telemetri Kartları
        stats_row = ctk.CTkFrame(container, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 8))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        self._lbl_latency = self._make_stat_card(stats_row, 0, "Gecikme (RTT)", "-- ms", ACCENT_SKY)
        self._lbl_bitrate = self._make_stat_card(stats_row, 1, "Veri Hızı", "0 kbps", ACCENT_EMERALD)
        self._lbl_client = self._make_stat_card(stats_row, 2, "Bağlı Cihaz", "Bekleniyor", TEXT_PRIMARY)

        # Ses Cihazı Seçimi ve PC Susturma Anahtarı
        dev_card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        dev_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            dev_card,
            text="WASAPI Loopback Ses Kaynağı",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        dev_row = ctk.CTkFrame(dev_card, fg_color="transparent")
        dev_row.pack(fill="x", padx=14, pady=(0, 8))

        self._device_var = ctk.StringVar(value="Cihaz aranıyor...")
        self._device_menu = ctk.CTkOptionMenu(
            dev_row,
            variable=self._device_var,
            values=["Cihaz aranıyor..."],
            fg_color=BG_PANEL,
            button_color="#283548",
            button_hover_color="#334155",
            dropdown_fg_color=BG_PANEL,
            text_color=TEXT_PRIMARY,
            height=34,
            command=lambda _v: self._update_mute_hint(),
        )
        self._device_menu.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            dev_row,
            text="Yenile",
            width=88,
            height=34,
            fg_color=BG_PANEL,
            hover_color="#334155",
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._refresh_devices,
        ).pack(side="right")

        mute_row = ctk.CTkFrame(dev_card, fg_color="transparent")
        mute_row.pack(fill="x", padx=14, pady=(0, 10))

        self._mute_pc_var = ctk.BooleanVar(value=True)
        self._mute_switch = ctk.CTkSwitch(
            mute_row,
            text="Yayın sırasında PC kulaklığını/hoparlörünü sustur",
            variable=self._mute_pc_var,
            progress_color=ACCENT_EMERALD,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
            command=self._update_mute_hint,
        )
        self._mute_switch.pack(anchor="w")

        self._lbl_mute_hint = ctk.CTkLabel(
            mute_row,
            text="Donanım susturma hazırlanıyor...",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._lbl_mute_hint.pack(anchor="w", pady=(2, 0))

        # Bağlantı Modu Kartı
        mode_card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        mode_card.pack(fill="x", pady=(0, 8))

        mode_top = ctk.CTkFrame(mode_card, fg_color="transparent")
        mode_top.pack(fill="x", padx=14, pady=(10, 6))

        ctk.CTkLabel(
            mode_top,
            text="Bağlantı Modu",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._mode_seg = ctk.CTkSegmentedButton(
            mode_top,
            values=["USB (ADB Reverse)", "Yerel Wi-Fi"],
            command=self._on_mode_change,
            selected_color=ACCENT_EMERALD,
            selected_hover_color=ACCENT_EMERALD_HOVER,
            unselected_color=BG_PANEL,
            fg_color=BG_PANEL,
        )
        self._mode_seg.set("USB (ADB Reverse)")
        self._mode_seg.pack(side="right")

        self._usb_panel = ctk.CTkFrame(mode_card, fg_color="transparent")
        self._usb_panel.pack(fill="x", padx=14, pady=(2, 10))

        self._lbl_adb_info = ctk.CTkLabel(
            self._usb_panel,
            text="ADB kontrol ediliyor...",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._lbl_adb_info.pack(side="left", fill="x", expand=True)

        self._btn_install_apk = ctk.CTkButton(
            self._usb_panel,
            text="Telefona APK Kur",
            height=32,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            font=("Segoe UI", 12, "bold"),
            command=self._install_apk_async,
        )
        self._btn_install_apk.pack(side="right", padx=(8, 0))

        self._btn_usb_bridge = ctk.CTkButton(
            self._usb_panel,
            text="USB Köprüsünü Başlat",
            height=32,
            fg_color="#0284C7",
            hover_color="#0369A1",
            font=("Segoe UI", 12, "bold"),
            command=self._setup_usb_bridge_async,
        )
        self._btn_usb_bridge.pack(side="right")

        self._wifi_panel = ctk.CTkFrame(mode_card, fg_color="transparent")
        ips = get_local_ipv4_addresses()
        ip_text = ", ".join(ips) if ips else "Yerel IP bulunamadı"
        self._lbl_wifi_info = ctk.CTkLabel(
            self._wifi_panel,
            text=f"Wi-Fi Modu: ADPCM + UDP FEC aktif • IP: {ip_text} (Port: {DEFAULT_PORT})",
            font=("Segoe UI", 11),
            text_color=ACCENT_SKY,
            anchor="w",
        )
        self._lbl_wifi_info.pack(fill="x", pady=(2, 10))

        # Ana Yayın Butonu
        self._btn_toggle = ctk.CTkButton(
            container,
            text="Yayını Başlat",
            height=42,
            corner_radius=12,
            fg_color=ACCENT_EMERALD,
            hover_color=ACCENT_EMERALD_HOVER,
            font=("Segoe UI", 14, "bold"),
            command=self._toggle_streaming,
        )
        self._btn_toggle.pack(fill="x", pady=(0, 8))

        # Canlı VU Metre
        vu_card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        vu_card.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            vu_card,
            text="Canlı Ses Seviyesi (48 kHz Stereo PCM)",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(8, 4))
        self._vu_meter = StereoVuMeter(vu_card)
        self._vu_meter.pack(fill="x", padx=14, pady=(0, 10))

        # Log Alanı
        log_card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        log_card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            log_card,
            text="Sistem Günlüğü",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(8, 4))
        self._log_box = ctk.CTkTextbox(
            log_card,
            height=96,
            fg_color="#0F172A",
            text_color="#CBD5E1",
            font=("Consolas", 11),
            corner_radius=8,
            state="disabled",
        )
        self._log_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def _make_stat_card(self, parent, col: int, title: str, initial: str, color: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        padx = (0, 6) if col == 0 else ((6, 0) if col == 2 else (4, 4))
        card.grid(row=0, column=col, sticky="nsew", padx=padx)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 11), text_color=TEXT_MUTED).pack(
            anchor="w", padx=12, pady=(8, 1)
        )
        lbl = ctk.CTkLabel(card, text=initial, font=("Segoe UI", 15, "bold"), text_color=color)
        lbl.pack(anchor="w", padx=12, pady=(0, 8))
        return lbl

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._log_queue.put(f"[{stamp}] {message}")

    def _on_mode_change(self, selected: str) -> None:
        if selected.startswith("USB"):
            self._wifi_panel.pack_forget()
            self._usb_panel.pack(fill="x", padx=14, pady=(2, 10))
        else:
            self._usb_panel.pack_forget()
            ips = get_local_ipv4_addresses()
            ip_text = ", ".join(ips) if ips else "Yerel IP bulunamadı"
            self._lbl_wifi_info.configure(
                text=f"Wi-Fi Modu: ADPCM + UDP FEC aktif • IP: {ip_text} (Port: {DEFAULT_PORT})"
            )
            self._wifi_panel.pack(fill="x", padx=14, pady=(2, 10))

    def _refresh_devices(self) -> None:
        try:
            self._devices = list_loopback_devices()
        except Exception as exc:
            self._devices = []
            self.log(f"Ses cihazları listelenemedi: {exc}")

        try:
            self._endpoints = audio_control.list_render_endpoints()
        except Exception:
            self._endpoints = []

        self._device_map.clear()
        if not self._devices:
            self._device_menu.configure(values=["Aktif WASAPI çıkış cihazı bulunamadı"])
            self._device_var.set("Aktif WASAPI çıkış cihazı bulunamadı")
            self._update_mute_hint()
            return

        labels: list[str] = []
        for dev in self._devices:
            label = dev.display_label
            self._device_map[label] = dev
            labels.append(label)

        self._device_menu.configure(values=labels)
        self._device_var.set(labels[0])
        self._update_mute_hint()
        self.log(f"{len(labels)} adet WASAPI Loopback ses cihazı bulundu.")

    def _update_mute_hint(self) -> None:
        if not self._mute_pc_var.get():
            self._lbl_mute_hint.configure(
                text="Kapalı: Ses hem PC çıkışından hem Bluetooth kulaklıktan çalar.",
                text_color=TEXT_MUTED,
            )
            return

        dev = self._device_map.get(self._device_var.get())
        if dev is None:
            self._lbl_mute_hint.configure(
                text="Yayın başlarken ses sessiz/sanal çıkışa yönlendirilir.",
                text_color=TEXT_MUTED,
            )
            return

        ep = audio_control.find_endpoint_for_loopback_name(dev.name, self._endpoints)
        sink = audio_control.find_silent_sink_endpoint(
            exclude_id=ep.device_id if ep else None,
            endpoints=self._endpoints,
        )
        if sink is not None:
            self._lbl_mute_hint.configure(
                text=f"Sessiz çıkışa aktarılıyor: {sink.friendly_name} (Windows sesi açık kalır)",
                text_color=ACCENT_EMERALD,
            )
            return

        if ep is not None and ep.hw_volume:
            self._lbl_mute_hint.configure(
                text="Donanım ses sıfırlama hazır • Durdurulunca eski ses seviyesi geri döner.",
                text_color=ACCENT_SKY,
            )
        elif ep is not None and ep.hw_mute:
            self._lbl_mute_hint.configure(
                text="Sessiz/sanal çıkış bulunamadı • Donanım susturma kullanılacak.",
                text_color=ACCENT_AMBER,
            )
        else:
            self._lbl_mute_hint.configure(
                text="Uyarı: Bu cihaz için sessiz çıkış veya susturma yöntemi bulunamadı.",
                text_color=ACCENT_AMBER,
            )

    def _check_adb_status(self) -> None:
        adb_path = adb_manager.find_adb()
        if adb_path is None:
            self._lbl_adb_info.configure(text="ADB bulunamadı (Kurulum eksik)", text_color=ACCENT_ROSE)
            self.log("Uyarı: adb.exe bulunamadı. USB modu için ADB gereklidir.")
        else:
            self._lbl_adb_info.configure(text=f"ADB hazır: {adb_path.name}", text_color=TEXT_MUTED)
            self.log(f"ADB algılandı: {adb_path}")

    def _setup_usb_bridge_async(self) -> None:
        self._btn_usb_bridge.configure(state="disabled", text="Kuruluyor...")

        def worker() -> None:
            ok, msg = adb_manager.setup_reverse(DEFAULT_PORT)
            self._adb_reverse_ready = ok
            self.log(msg)
            self.after(0, lambda: self._on_usb_bridge_result(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_usb_bridge_result(self, ok: bool, msg: str) -> None:
        self._btn_usb_bridge.configure(state="normal", text="USB Köprüsünü Başlat")
        if ok:
            self._lbl_adb_info.configure(text=msg, text_color=ACCENT_EMERALD)
        else:
            self._lbl_adb_info.configure(text=msg, text_color=ACCENT_AMBER)

    def _install_apk_async(self) -> None:
        self._btn_install_apk.configure(state="disabled", text="Kuruluyor...")

        def worker() -> None:
            ok, msg = adb_manager.install_apk()
            self.log(msg)
            self.after(0, lambda: self._on_install_apk_result(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_apk_result(self, ok: bool, msg: str) -> None:
        self._btn_install_apk.configure(state="normal", text="Telefona APK Kur")
        if ok:
            self._lbl_adb_info.configure(text=msg, text_color=ACCENT_EMERALD)
        else:
            self._lbl_adb_info.configure(text=msg, text_color=ACCENT_AMBER)

    def _toggle_streaming(self) -> None:
        if self._streaming:
            self._stop_streaming()
        else:
            self._start_streaming()

    def _start_streaming(self) -> None:
        selected_label = self._device_var.get()
        device = self._device_map.get(selected_label)
        if device is None:
            self.log("Hata: Lütfen geçerli bir WASAPI Loopback ses cihazı seçin.")
            return

        is_usb = self._mode_seg.get().startswith("USB")
        bind_host = "127.0.0.1" if is_usb else "0.0.0.0"
        mute_pc = bool(self._mute_pc_var.get())
        self._is_usb_mode = is_usb
        self._last_reverse_check = time.monotonic()

        self._btn_toggle.configure(state="disabled", text="Başlatılıyor...")

        def start_worker() -> None:
            if is_usb:
                ok, msg = adb_manager.setup_reverse(DEFAULT_PORT)
                self._adb_reverse_ready = ok
                self.log(msg)
                self.after(0, lambda: self._on_usb_bridge_result(ok, msg))
                if not ok:
                    self.after(0, self._restore_stopped_button)
                    return

            capture_device = device
            if mute_pc:
                capture_device = self._activate_pc_silence(device)

            server = AudioBridgeServer(
                host=bind_host,
                port=DEFAULT_PORT,
                on_log=self.log,
                mode="usb" if is_usb else "wifi",
            )
            capture = WasapiLoopbackCapture(
                device=capture_device,
                on_frame=server.push_audio_frame,
                on_vu=self._update_vu_levels,
                on_log=self.log,
            )
            try:
                server.start()
                capture.start()
            except Exception as exc:
                self.log(f"Yayın başlatılamadı: {exc}")
                capture.stop()
                server.stop()
                self._silencer.restore()
                self.after(0, self._restore_stopped_button)
                return

            self._server = server
            self._capture = capture
            self._streaming = True
            self.after(0, self._on_started_ui)

        threading.Thread(target=start_worker, daemon=True).start()

    def _activate_pc_silence(self, selected_device: LoopbackDevice) -> LoopbackDevice:
        try:
            endpoints = audio_control.list_render_endpoints()
            target_ep = audio_control.find_endpoint_for_loopback_name(selected_device.name, endpoints)

            # 1. Öncelik: route_silent (Windows sesini mute etmeden sanal/sessiz çıkışa yönlendir)
            sink_ep = audio_control.find_silent_sink_endpoint(
                exclude_id=target_ep.device_id if target_ep else None,
                endpoints=endpoints,
            )
            if sink_ep is not None:
                all_lb = list_loopback_devices()
                sink_lb = next(
                    (
                        d
                        for d in all_lb
                        if d.name.removesuffix(" [Loopback]").strip().lower()
                        == sink_ep.friendly_name.strip().lower()
                        or sink_ep.friendly_name.strip().lower() in d.name.lower()
                    ),
                    None,
                )
                if sink_lb is not None and self._silencer.activate_silent_route(sink_ep.device_id):
                    self.log(
                        f"Windows sesi açık tutuldu, ses sessiz çıkışa aktarıldı: {sink_ep.friendly_name}"
                    )
                    return sink_lb

            # 2. Öncelik: Donanım ses sıfırlama (Mute ikonu çıkarmadan ses seviyesini sıfırlar)
            if (
                target_ep is not None
                and target_ep.hw_volume
                and self._silencer.activate_hardware_zero_vol(target_ep.device_id)
            ):
                self.log(f"PC ses seviyesi sıfırlandı: {target_ep.friendly_name}")
                return selected_device

            # 3. Son çare: Donanım mute
            if (
                target_ep is not None
                and target_ep.hw_mute
                and self._silencer.activate_hardware_mute(target_ep.device_id)
            ):
                self.log(f"PC çıkışı susturuldu (donanım mute): {target_ep.friendly_name}")
                return selected_device

            self.log("Uyarı: PC çıkışı susturulamadı, ses her iki cihazdan da çalabilir.")
        except Exception as exc:
            self.log(f"PC susturma uygulanamadı: {exc}")
        return selected_device

    def _restore_stopped_button(self) -> None:
        self._btn_toggle.configure(
            state="normal",
            text="Yayını Başlat",
            fg_color=ACCENT_EMERALD,
            hover_color=ACCENT_EMERALD_HOVER,
        )

    def _on_started_ui(self) -> None:
        self._device_menu.configure(state="disabled")
        self._mute_switch.configure(state="disabled")
        self._mode_seg.configure(state="disabled")
        self._btn_toggle.configure(
            state="normal",
            text="Yayını Durdur",
            fg_color=ACCENT_ROSE,
            hover_color=ACCENT_ROSE_HOVER,
        )
        self._status_badge.configure(text="● Bağlantı Bekleniyor", text_color=ACCENT_AMBER)

    def _stop_streaming(self) -> None:
        was_streaming = self._streaming
        self._streaming = False
        if self._capture is not None:
            self._capture.stop()
            self._capture = None
        if self._server is not None:
            self._server.stop()
            self._server = None

        restored = self._silencer.restore()
        if restored:
            self.log("PC kulaklığı/ses çıkışı eski durumuna döndürüldü.")

        self._update_vu_levels(0.0, 0.0)
        self._vu_meter.set_levels(0.0, 0.0)
        self._device_menu.configure(state="normal")
        self._mute_switch.configure(state="normal")
        self._mode_seg.configure(state="normal")
        self._restore_stopped_button()
        self._status_badge.configure(text="● Hazır", text_color=TEXT_MUTED)
        self._lbl_latency.configure(text="-- ms")
        self._lbl_bitrate.configure(text="0 kbps")
        self._lbl_client.configure(text="Durduruldu" if was_streaming else "Bekleniyor")
        if was_streaming:
            self.log("Yayın durduruldu.")

    def _update_vu_levels(self, left: float, right: float) -> None:
        with self._vu_lock:
            self._vu_left = left
            self._vu_right = right

    def _ui_tick(self) -> None:
        # Günlük kuyruğunu boşalt
        flushed = False
        while True:
            try:
                line = self._log_queue.get_nowait()
            except queue.Empty:
                break
            if not flushed:
                self._log_box.configure(state="normal")
                flushed = True
            self._log_box.insert("end", line + "\n")
        if flushed:
            self._log_box.see("end")
            self._log_box.configure(state="disabled")

        # VU metre güncellemesi (sessizlikte yumuşak sönümleme)
        if self._streaming and self._capture is not None:
            silence_age = time.monotonic() - self._capture.last_audio_time
            with self._vu_lock:
                if silence_age > 0.12:
                    self._vu_left *= 0.72
                    self._vu_right *= 0.72
                l_val, r_val = self._vu_left, self._vu_right
            self._vu_meter.set_levels(l_val, r_val)

        # Telemetri güncellemesi & USB watchdog
        tooltip = "BTBridge — Hazır"
        if self._streaming and self._server is not None:
            stats = self._server.get_stats()
            if stats.connected:
                self._status_badge.configure(text="● Bağlı", text_color=ACCENT_EMERALD)
                self._lbl_latency.configure(
                    text=f"{stats.rtt_ms} ms" if stats.rtt_ms is not None else "Ölçülüyor..."
                )
                self._lbl_bitrate.configure(text=f"{stats.kbps:.0f} kbps")
                addr_only = (stats.client_addr or "Bağlı").rsplit(":", 1)[0]
                self._lbl_client.configure(text=f"{addr_only} ({stats.transport_label})")
                tooltip = (
                    f"BTBridge — {stats.transport_label} ({stats.rtt_ms} ms)"
                    if stats.rtt_ms is not None
                    else f"BTBridge — {stats.transport_label}"
                )
            else:
                self._status_badge.configure(text="● Bağlantı Bekleniyor", text_color=ACCENT_AMBER)
                self._lbl_latency.configure(text="-- ms")
                self._lbl_bitrate.configure(text="0 kbps")
                self._lbl_client.configure(text="Bekleniyor")
                tooltip = "BTBridge — Bağlantı Bekleniyor"
                self._maybe_repair_usb_reverse()

        if tooltip != self._last_tray_tooltip:
            self._last_tray_tooltip = tooltip
            self._tray.update_tooltip(tooltip)

        self.after(33, self._ui_tick)

    def _maybe_repair_usb_reverse(self) -> None:
        if not self._is_usb_mode or self._reverse_checking:
            return
        now = time.monotonic()
        if (now - self._last_reverse_check) < 3.5:
            return
        self._last_reverse_check = now
        self._reverse_checking = True

        def watchdog_worker() -> None:
            try:
                if not adb_manager.is_reverse_active(DEFAULT_PORT):
                    ok, msg = adb_manager.setup_reverse(DEFAULT_PORT)
                    self._adb_reverse_ready = ok
                    if ok:
                        self.log(f"USB köprüsü otomatik yenilendi: {msg}")
                    self.after(0, lambda: self._on_usb_bridge_result(ok, msg))
            finally:
                self._reverse_checking = False

        threading.Thread(target=watchdog_worker, daemon=True).start()

    def _hide_to_tray(self) -> None:
        self.withdraw()
        self._tray.notify_minimized()

    def _restore_from_tray(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit_completely(self) -> None:
        self._stop_streaming()
        self._tray.stop()
        self.destroy()
