"""BTBridge TCP sunucusu ve sahte istemci ile uçtan uca akış testleri."""

from __future__ import annotations

from pathlib import Path
import socket
import sys
import time

import numpy as np

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

from dsp import (  # noqa: E402
    AudioResamplerConverter,
    FramePacketizer,
    decode_stereo_ima_adpcm,
)
from protocol import (  # noqa: E402
    ADPCM_FEC_BYTES,
    ADPCM_FRAME_BYTES,
    AUDIO_PAYLOAD_BYTES,
    HEADER_SIZE,
    MSG_AUDIO,
    MSG_AUDIO_ADPCM,
    MSG_AUDIO_ADPCM_FEC,
    MSG_PING,
    MSG_PONG,
    MSG_UDP_HELLO,
    now_monotonic_ms,
    pack_packet,
    recv_exact,
    unpack_header,
)
from server import AudioBridgeServer  # noqa: E402


def _connect_mock_client(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(3.0)
    sock.connect(("127.0.0.1", port))
    return sock


def test_live_tcp_audio_stream_and_ping_pong() -> None:
    logs: list[str] = []
    server = AudioBridgeServer(host="127.0.0.1", port=0, on_log=logs.append)
    server.start()
    try:
        client = _connect_mock_client(server.bound_port)
        try:
            # Sunucunun istemciyi kabul etmesi için kısa bekleme
            deadline = time.monotonic() + 2.0
            while not server.get_stats().connected and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.get_stats().connected

            # İstemciden Ping gönderip sunucunun Pong cevabını ve sunucu Ping'ine Pong yanıtını test et
            client_ping_ts = 123456
            client.sendall(pack_packet(MSG_PING, 99, client_ping_ts))

            # 44.1 kHz -> 48 kHz dönüştürülmüş ses karelerini sunucuya besle
            conv = AudioResamplerConverter(src_rate=44100, src_channels=2, src_format="float32")
            packetizer = FramePacketizer()
            t = np.arange(4410, dtype=np.float64) / 44100.0
            tone = (0.4 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
            stereo = np.column_stack((tone, tone)).astype("<f4").tobytes()
            pcm_bytes, _, _ = conv.process(stereo)
            frames = packetizer.push(pcm_bytes)
            assert len(frames) >= 9

            for frame in frames:
                server.push_audio_frame(frame)

            received_audio: list[tuple[int, bytes]] = []
            got_client_pong = False
            replied_server_ping = False

            read_deadline = time.monotonic() + 3.0
            while time.monotonic() < read_deadline and (
                len(received_audio) < len(frames) or not got_client_pong or not replied_server_ping
            ):
                hdr = unpack_header(recv_exact(client, HEADER_SIZE))
                payload = recv_exact(client, hdr.payload_len)
                if hdr.msg_type == MSG_PONG and hdr.seq == 99 and hdr.timestamp_ms == client_ping_ts:
                    got_client_pong = True
                elif hdr.msg_type == MSG_PING:
                    # Sunucu Ping'ini yanıtla ki server RTT hesaplasın
                    client.sendall(pack_packet(MSG_PONG, hdr.seq, hdr.timestamp_ms))
                    replied_server_ping = True
                elif hdr.msg_type == MSG_AUDIO:
                    assert len(payload) == AUDIO_PAYLOAD_BYTES
                    received_audio.append((hdr.seq, payload))

            assert got_client_pong
            assert replied_server_ping
            assert len(received_audio) == len(frames)
            assert [seq for seq, _ in received_audio] == list(range(1, len(frames) + 1))

            # Sunucunun RTT değerini güncellemesini bekle
            rtt_deadline = time.monotonic() + 2.0
            while server.get_stats().rtt_ms is None and time.monotonic() < rtt_deadline:
                time.sleep(0.02)

            stats = server.get_stats()
            assert stats.rtt_ms is not None
            assert 0 <= stats.rtt_ms < 500
            assert stats.packets_sent >= len(frames)
        finally:
            client.close()

        # İstemci kapandıktan sonra yeniden bağlanabilme testi
        time.sleep(0.1)
        client2 = _connect_mock_client(server.bound_port)
        try:
            client2.sendall(pack_packet(MSG_PING, 1, now_monotonic_ms()))
            seen_pong = False
            for _ in range(5):
                hdr = unpack_header(recv_exact(client2, HEADER_SIZE))
                _ = recv_exact(client2, hdr.payload_len)
                if hdr.msg_type == MSG_PONG and hdr.seq == 1:
                    seen_pong = True
                    break
            assert seen_pong
        finally:
            client2.close()
    finally:
        server.stop()


def test_wifi_mode_tcp_adpcm_fallback_and_udp_fec_recovery() -> None:
    server = AudioBridgeServer(host="127.0.0.1", port=0, mode="wifi")
    server.start()
    try:
        client = _connect_mock_client(server.bound_port)
        try:
            deadline = time.monotonic() + 2.0
            while not server.get_stats().connected and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.get_stats().connected

            # 1) UDP HELLO göndermeden önce TCP üzerinden 486B ADPCM yedek akışı gelir
            t = np.arange(480 * 3, dtype=np.float64) / 48000.0
            sig = np.rint(0.4 * np.sin(2.0 * np.pi * 440.0 * t) * 32767.0).astype("<i2")
            pcm_all = np.column_stack((sig, sig)).astype("<i2").tobytes()
            for idx in range(3):
                server.push_audio_frame(pcm_all[idx * 1920 : (idx + 1) * 1920])

            tcp_adpcm = 0
            read_deadline = time.monotonic() + 2.0
            while tcp_adpcm < 3 and time.monotonic() < read_deadline:
                hdr = unpack_header(recv_exact(client, HEADER_SIZE))
                payload = recv_exact(client, hdr.payload_len)
                if hdr.msg_type == MSG_AUDIO_ADPCM:
                    assert len(payload) == ADPCM_FRAME_BYTES
                    assert len(decode_stereo_ima_adpcm(payload)) == AUDIO_PAYLOAD_BYTES
                    tcp_adpcm += 1
                elif hdr.msg_type == MSG_PING:
                    client.sendall(pack_packet(MSG_PONG, hdr.seq, hdr.timestamp_ms))
            assert tcp_adpcm == 3
            assert server.get_stats().transport_label == "Wi-Fi TCP+ADPCM"

            # 2) UDP HELLO gönderilince UDP+FEC akışına geçer ve 1 paket kaybı FEC ile kurtarılır
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.settimeout(2.0)
            try:
                udp_sock.sendto(pack_packet(MSG_UDP_HELLO, 1, now_monotonic_ms()), ("127.0.0.1", server.bound_port))
                wait_udp = time.monotonic() + 2.0
                while server.get_stats().transport_label != "Wi-Fi UDP+FEC" and time.monotonic() < wait_udp:
                    time.sleep(0.02)
                assert server.get_stats().transport_label == "Wi-Fi UDP+FEC"

                # 4 ardışık kare gönder
                for i in range(4):
                    server.push_audio_frame(pcm_all[(i % 3) * 1920 : ((i % 3) + 1) * 1920])

                udp_packets: list[tuple[int, bytes]] = []
                udp_deadline = time.monotonic() + 2.0
                while len(udp_packets) < 4 and time.monotonic() < udp_deadline:
                    pkt, _ = udp_sock.recvfrom(2048)
                    uhdr = unpack_header(pkt[:HEADER_SIZE])
                    assert uhdr.msg_type == MSG_AUDIO_ADPCM_FEC
                    assert uhdr.payload_len == ADPCM_FEC_BYTES
                    udp_packets.append((uhdr.seq, pkt[HEADER_SIZE:]))

                assert len(udp_packets) == 4
                # 2. paket (indeks 1) ağda kaybolmuş gibi simüle et -> 3. paketin (indeks 2) ikinci 486B dilimi kurtarır
                lost_curr = udp_packets[1][1][:ADPCM_FRAME_BYTES]
                fec_prev_from_next = udp_packets[2][1][ADPCM_FRAME_BYTES:]
                assert fec_prev_from_next == lost_curr
            finally:
                udp_sock.close()
        finally:
            client.close()
    finally:
        server.stop()
