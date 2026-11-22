"""Windows WASAPI Loopback ses yakalama modülü."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Optional

import pyaudiowpatch as pyaudio

from dsp import AudioResamplerConverter, FramePacketizer


@dataclass(frozen=True, slots=True)
class LoopbackDevice:
    """Aktif bir Windows WASAPI Loopback ses çıkış cihazını temsil eder."""

    index: int
    name: str
    sample_rate: int
    channels: int
    is_default: bool = False

    @property
    def display_label(self) -> str:
        prefix = "★ [Varsayılan] " if self.is_default else ""
        return f"{prefix}{self.name} ({self.sample_rate} Hz, {self.channels}ch)"


def list_loopback_devices() -> list[LoopbackDevice]:
    """Sistemdeki tüm aktif Windows WASAPI Loopback çıkış cihazlarını listeler."""
    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_idx = int(wasapi_info.get("defaultOutputDevice", -1))
        default_name = ""
        if default_idx >= 0:
            default_info = p.get_device_info_by_index(default_idx)
            default_name = str(default_info.get("name", ""))

        devices: list[LoopbackDevice] = []
        for dev in p.get_loopback_device_info_generator():
            name = str(dev.get("name", "Bilinmeyen Cihaz"))
            is_default = bool(default_name and default_name in name)
            devices.append(
                LoopbackDevice(
                    index=int(dev["index"]),
                    name=name,
                    sample_rate=int(round(float(dev.get("defaultSampleRate", 48000)))),
                    channels=max(1, int(dev.get("maxInputChannels", 2))),
                    is_default=is_default,
                )
            )

        devices.sort(key=lambda d: (not d.is_default, d.name.lower()))
        return devices
    finally:
        p.terminate()


class WasapiLoopbackCapture:
    """Seçilen WASAPI Loopback cihazından canlı ses yakalar ve 10 ms PCM kareleri üretir."""

    def __init__(
        self,
        device: LoopbackDevice,
        on_frame: Callable[[bytes], None],
        on_vu: Optional[Callable[[float, float], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.device = device
        self._on_frame = on_frame
        self._on_vu = on_vu
        self._on_log = on_log

        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream = None
        self._converter: Optional[AudioResamplerConverter] = None
        self._packetizer = FramePacketizer()
        self._lock = threading.Lock()
        self._running = False
        self.last_audio_time: float = 0.0

    def _log(self, msg: str) -> None:
        if self._on_log:
            self._on_log(msg)

    def start(self) -> None:
        """WASAPI Loopback ses yakalamayı başlatır."""
        with self._lock:
            if self._running:
                return
            self._pa = pyaudio.PyAudio()
            frames_per_buffer = max(64, int(self.device.sample_rate * 0.01))

            stream_format = pyaudio.paFloat32
            format_name = "float32"
            try:
                self._converter = AudioResamplerConverter(
                    src_rate=self.device.sample_rate,
                    src_channels=self.device.channels,
                    src_format=format_name,
                )
                self._packetizer.reset()
                self._stream = self._pa.open(
                    format=stream_format,
                    channels=self.device.channels,
                    rate=self.device.sample_rate,
                    input=True,
                    input_device_index=self.device.index,
                    frames_per_buffer=frames_per_buffer,
                    stream_callback=self._audio_callback,
                )
            except OSError:
                # Bazı sürücüler float32 yerine int16 tercih edebilir
                stream_format = pyaudio.paInt16
                format_name = "int16"
                self._converter = AudioResamplerConverter(
                    src_rate=self.device.sample_rate,
                    src_channels=self.device.channels,
                    src_format=format_name,
                )
                self._packetizer.reset()
                self._stream = self._pa.open(
                    format=stream_format,
                    channels=self.device.channels,
                    rate=self.device.sample_rate,
                    input=True,
                    input_device_index=self.device.index,
                    frames_per_buffer=frames_per_buffer,
                    stream_callback=self._audio_callback,
                )

            self._running = True
            self.last_audio_time = time.monotonic()
            self._stream.start_stream()
            self._log(
                f"Ses yakalama başladı: {self.device.name} "
                f"({self.device.sample_rate} Hz, {self.device.channels}ch, {format_name} -> 48kHz/16-bit Stereo)"
            )

    def _audio_callback(self, in_data, frame_count, time_info, status_flags):
        if not self._running or not in_data or self._converter is None:
            return (None, pyaudio.paContinue)
        try:
            pcm_bytes, vu_l, vu_r = self._converter.process(in_data)
            self.last_audio_time = time.monotonic()
            if self._on_vu:
                self._on_vu(vu_l, vu_r)
            if pcm_bytes:
                for frame in self._packetizer.push(pcm_bytes):
                    self._on_frame(frame)
        except Exception as exc:
            self._log(f"Ses işleme hatası: {exc}")
        return (None, pyaudio.paContinue)

    def stop(self) -> None:
        """WASAPI Loopback ses akışını güvenli biçimde durdurur."""
        with self._lock:
            self._running = False
            if self._stream is not None:
                try:
                    if self._stream.is_active():
                        self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            if self._pa is not None:
                try:
                    self._pa.terminate()
                except Exception:
                    pass
                self._pa = None
            self._converter = None
            self._packetizer.reset()
