"""BTBridge ikili protokol birim testleri."""

from __future__ import annotations

from pathlib import Path
import socket
import struct
import sys

import pytest

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

from protocol import (  # noqa: E402
    AUDIO_PAYLOAD_BYTES,
    HEADER_SIZE,
    MAGIC,
    MAX_PAYLOAD_LEN,
    MSG_AUDIO,
    MSG_PING,
    MSG_PONG,
    pack_packet,
    recv_exact,
    unpack_header,
)


def test_header_size_and_constants() -> None:
    assert HEADER_SIZE == 17
    assert AUDIO_PAYLOAD_BYTES == 1920


@pytest.mark.parametrize(
    ("msg_type", "seq", "ts", "payload"),
    [
        (MSG_AUDIO, 1, 123456789, b"\x01\x02" * 960),
        (MSG_PING, 0xFFFFFFFF, 0x123456789ABCDEF0, b""),
        (MSG_PONG, 42, 998877665544, b""),
    ],
)
def test_pack_unpack_roundtrip(msg_type: int, seq: int, ts: int, payload: bytes) -> None:
    pkt = pack_packet(msg_type, seq, ts, payload)
    assert len(pkt) == HEADER_SIZE + len(payload)

    hdr = unpack_header(pkt[:HEADER_SIZE])
    assert hdr.msg_type == msg_type
    assert hdr.seq == seq
    assert hdr.timestamp_ms == ts
    assert hdr.payload_len == len(payload)
    assert pkt[HEADER_SIZE:] == payload


def test_header_big_endian_layout() -> None:
    pkt = pack_packet(MSG_AUDIO, 0x01020304, 0x0102030405060708, b"abcd")
    magic, msg_type, seq, ts, plen = struct.unpack(">HBIQH", pkt[:17])
    assert magic == MAGIC
    assert msg_type == MSG_AUDIO
    assert seq == 0x01020304
    assert ts == 0x0102030405060708
    assert plen == 4


def test_invalid_headers_raise() -> None:
    with pytest.raises(ValueError):
        unpack_header(b"short")

    bad_magic = struct.pack(">HBIQH", 0xBEEF, MSG_PING, 1, 100, 0)
    with pytest.raises(ValueError):
        unpack_header(bad_magic)

    bad_type = struct.pack(">HBIQH", MAGIC, 99, 1, 100, 0)
    with pytest.raises(ValueError):
        unpack_header(bad_type)

    oversize_len = struct.pack(">HBIQH", MAGIC, MSG_AUDIO, 1, 100, MAX_PAYLOAD_LEN + 1)
    with pytest.raises(ValueError):
        unpack_header(oversize_len)

    with pytest.raises(ValueError):
        pack_packet(99, 1, 100, b"")

    with pytest.raises(ValueError):
        pack_packet(MSG_AUDIO, 1, 100, b"x" * (MAX_PAYLOAD_LEN + 1))


def test_recv_exact_fragmented_socketpair() -> None:
    s1, s2 = socket.socketpair()
    try:
        pkt = pack_packet(MSG_AUDIO, 7, 555, b"Z" * 1920)
        # Parçalı gönderim simülasyonu
        s1.sendall(pkt[:5])
        s1.sendall(pkt[5:17])
        s1.sendall(pkt[17:500])
        s1.sendall(pkt[500:])
        s1.close()

        hdr_bytes = recv_exact(s2, HEADER_SIZE)
        hdr = unpack_header(hdr_bytes)
        body = recv_exact(s2, hdr.payload_len)
        assert hdr.seq == 7
        assert hdr.timestamp_ms == 555
        assert body == b"Z" * 1920

        with pytest.raises(ConnectionError):
            recv_exact(s2, 1)
    finally:
        s1.close()
        s2.close()


def test_recv_exact_preserves_partial_bytes_across_socket_timeout() -> None:
    import threading

    s1, s2 = socket.socketpair()
    try:
        s2.settimeout(0.05)
        pkt = pack_packet(MSG_PING, 12, 3456)
        s1.sendall(pkt[:7])

        def delayed_rest() -> None:
            time.sleep(0.12)
            s1.sendall(pkt[7:])

        import time

        t = threading.Thread(target=delayed_rest, daemon=True)
        t.start()
        hdr_bytes = recv_exact(s2, HEADER_SIZE, idle_timeout=2.0)
        hdr = unpack_header(hdr_bytes)
        assert hdr.msg_type == MSG_PING
        assert hdr.seq == 12
        assert hdr.timestamp_ms == 3456
        t.join(timeout=1.0)
    finally:
        s1.close()
        s2.close()
