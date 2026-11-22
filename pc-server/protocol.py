"""BTBridge ikili ağ protokolü ve çerçeveleme yardımcıları."""

from __future__ import annotations

from dataclasses import dataclass
import socket
import struct
import threading
import time
from typing import Optional

MAGIC: int = 0xB7B7

MSG_AUDIO: int = 1
MSG_PING: int = 2
MSG_PONG: int = 3
MSG_AUDIO_ADPCM: int = 4
MSG_UDP_HELLO: int = 5
MSG_AUDIO_ADPCM_FEC: int = 6
VALID_TYPES = frozenset(
    {
        MSG_AUDIO,
        MSG_PING,
        MSG_PONG,
        MSG_AUDIO_ADPCM,
        MSG_UDP_HELLO,
        MSG_AUDIO_ADPCM_FEC,
    }
)

# Big-Endian: uint16 Magic, uint8 Type, uint32 Seq, uint64 TimestampMs, uint16 PayloadLen
HEADER_FORMAT: str = ">HBIQH"
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)  # 17 bytes
MAX_PAYLOAD_LEN: int = 8192

SAMPLE_RATE: int = 48000
CHANNELS: int = 2
SAMPLE_WIDTH_BYTES: int = 2  # 16-bit signed PCM
FRAME_MS: int = 10
FRAME_SAMPLES: int = SAMPLE_RATE * FRAME_MS // 1000  # 480 stereo frames
AUDIO_PAYLOAD_BYTES: int = FRAME_SAMPLES * CHANNELS * SAMPLE_WIDTH_BYTES  # 1920 bytes
ADPCM_STATE_BYTES: int = 6  # <hBhB (pred_L, idx_L, pred_R, idx_R)
ADPCM_CHANNEL_BYTES: int = FRAME_SAMPLES // 2  # 240 bytes
ADPCM_FRAME_BYTES: int = ADPCM_STATE_BYTES + (ADPCM_CHANNEL_BYTES * 2)  # 486 bytes
ADPCM_FEC_BYTES: int = ADPCM_FRAME_BYTES * 2  # 972 bytes
DEFAULT_PORT: int = 50005


@dataclass(frozen=True, slots=True)
class PacketHeader:
    """17 baytlık BTBridge paket başlığı."""

    msg_type: int
    seq: int
    timestamp_ms: int
    payload_len: int


def now_monotonic_ms() -> int:
    """Milisaniye cinsinden monotonik sistem saati döndürür."""
    return time.monotonic_ns() // 1_000_000


def pack_packet(
    msg_type: int,
    seq: int,
    timestamp_ms: int,
    payload: bytes = b"",
) -> bytes:
    """Başlık ve yükü 17+N baytlık ikili pakete dönüştürür."""
    if msg_type not in VALID_TYPES:
        raise ValueError(f"Geçersiz paket tipi: {msg_type}")
    payload_len = len(payload)
    if payload_len > MAX_PAYLOAD_LEN:
        raise ValueError(f"Yük boyutu çok büyük: {payload_len} > {MAX_PAYLOAD_LEN}")
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        msg_type,
        seq & 0xFFFFFFFF,
        timestamp_ms & 0xFFFFFFFFFFFFFFFF,
        payload_len,
    )
    return header + payload if payload else header


def unpack_header(data: bytes) -> PacketHeader:
    """17 baytlık ham başlığı doğrular ve PacketHeader döndürür."""
    if len(data) != HEADER_SIZE:
        raise ValueError(f"Başlık uzunluğu {HEADER_SIZE} bayt olmalı, gelen: {len(data)}")
    magic, msg_type, seq, timestamp_ms, payload_len = struct.unpack(HEADER_FORMAT, data)
    if magic != MAGIC:
        raise ValueError(f"Geçersiz paket imzası: 0x{magic:04X}")
    if msg_type not in VALID_TYPES:
        raise ValueError(f"Bilinmeyen paket tipi: {msg_type}")
    if payload_len > MAX_PAYLOAD_LEN:
        raise ValueError(f"Geçersiz yük uzunluğu: {payload_len}")
    return PacketHeader(
        msg_type=msg_type,
        seq=seq,
        timestamp_ms=timestamp_ms,
        payload_len=payload_len,
    )


def recv_exact(
    sock: socket.socket,
    n: int,
    stop_event: Optional[threading.Event] = None,
    idle_timeout: float = 10.0,
) -> bytes:
    """Soketten tam olarak n bayt okur; timeout'ta kısmi baytları korur."""
    if n == 0:
        return b""
    buf = bytearray()
    last_rx = time.monotonic()
    while len(buf) < n:
        if stop_event is not None and stop_event.is_set():
            raise ConnectionError("Soket durduruldu")
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            if stop_event is not None and stop_event.is_set():
                raise ConnectionError("Soket durduruldu")
            if (time.monotonic() - last_rx) >= idle_timeout:
                raise TimeoutError("Uzak soketten uzun süredir veri alınamadı")
            continue
        if not chunk:
            raise ConnectionError("Uzak soket bağlantısı kapandı")
        buf.extend(chunk)
        last_rx = time.monotonic()
    return bytes(buf)
