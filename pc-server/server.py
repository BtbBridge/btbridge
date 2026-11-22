"""Düşük gecikmeli TCP ses sunucusu ve Ping/Pong RTT ölçüm motoru."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import select
import socket
import threading
import time
from typing import Callable, Optional

from dsp import StereoImaAdpcmEncoder
from protocol import (
    DEFAULT_PORT,
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


@dataclass(frozen=True, slots=True)
class ServerStats:
    """Sunucu ve bağlantı telemetrisi."""

    running: bool
    connected: bool
    client_addr: Optional[str]
    rtt_ms: Optional[int]
    kbps: float
    packets_sent: int
    packets_dropped: int
    transport_label: str = "USB PCM"


def get_local_ipv4_addresses() -> list[str]:
    """Yerel ağdaki IPv4 adreslerini Wi-Fi modu bilgisi için döndürür."""
    ips: list[str] = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            primary_ip = probe.getsockname()[0]
            if primary_ip and not primary_ip.startswith("127."):
                ips.append(primary_ip)
        finally:
            probe.close()
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = str(info[4][0])
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass

    return ips


class AudioBridgeServer:
    """TCP_NODELAY aktif, tek istemcili düşük gecikmeli ses sunucusu."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
        on_log: Optional[Callable[[str], None]] = None,
        mode: str = "usb",
    ) -> None:
        self.host = host
        self.port = port
        self._on_log = on_log
        self.mode = mode.lower()

        self._server_sock: Optional[socket.socket] = None
        self._udp_sock: Optional[socket.socket] = None
        self.bound_port: int = port

        self._stop_event = threading.Event()
        self._accept_thread: Optional[threading.Thread] = None
        self._udp_thread: Optional[threading.Thread] = None

        self._client_lock = threading.Lock()
        self._client_sock: Optional[socket.socket] = None
        self._client_addr: Optional[str] = None
        self._udp_client_addr: Optional[tuple[str, int]] = None
        self._client_stop: Optional[threading.Event] = None
        self._client_threads: list[threading.Thread] = []

        self._adpcm_encoder = StereoImaAdpcmEncoder()
        self._prev_adpcm_frame: Optional[bytes] = None

        self._queue_cond = threading.Condition()
        queue_len = 16 if self.mode == "wifi" else 12
        self._audio_queue: deque[tuple[int, bytes]] = deque(maxlen=queue_len)
        self._ctrl_queue: deque[bytes] = deque(maxlen=32)

        self._audio_seq: int = 0
        self._ping_seq: int = 0
        self._packets_sent: int = 0
        self._packets_dropped: int = 0
        self._rtt_ms: Optional[int] = None

        self._rate_lock = threading.Lock()
        self._bytes_window: int = 0
        self._last_rate_time: float = time.monotonic()
        self._kbps: float = 0.0

    def _log(self, msg: str) -> None:
        if self._on_log:
            self._on_log(msg)

    def start(self) -> None:
        """TCP dinleme soketini açar ve bağlantı kabul iş parçacığını başlatır."""
        if self._server_sock is not None:
            return
        self._stop_event.clear()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(2)
        sock.settimeout(0.5)
        self._server_sock = sock
        self.bound_port = int(sock.getsockname()[1])

        self._accept_thread = threading.Thread(
            target=self._accept_loop,
            name="BTBridge-Accept",
            daemon=True,
        )
        self._accept_thread.start()

        if self.mode == "wifi":
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)
            except OSError:
                pass
            try:
                udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
                udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            except OSError:
                pass
            udp_sock.settimeout(0.5)
            udp_sock.bind((self.host, self.bound_port))
            self._udp_sock = udp_sock
            self._udp_thread = threading.Thread(
                target=self._udp_listener_loop,
                name="BTBridge-UDP",
                daemon=True,
            )
            self._udp_thread.start()
            self._log(
                f"Sunucu dinleniyor: {self.host}:{self.bound_port} (TCP + Wi-Fi UDP FEC / ADPCM)"
            )
        else:
            self._log(f"TCP sunucusu dinleniyor: {self.host}:{self.bound_port} (TCP_NODELAY=True)")

    def stop(self) -> None:
        """Sunucuyu ve aktif istemci bağlantısını temiz biçimde kapatır."""
        self._stop_event.set()
        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None

        if self._udp_sock is not None:
            try:
                self._udp_sock.close()
            except OSError:
                pass
            self._udp_sock = None

        self._disconnect_active_client()

        if self._accept_thread is not None and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)
        self._accept_thread = None

        if self._udp_thread is not None and self._udp_thread.is_alive():
            self._udp_thread.join(timeout=2.0)
        self._udp_thread = None

    def push_audio_frame(self, pcm_bytes: bytes) -> None:
        """Bir 10 ms ses karesini bağlı istemcinin kuyruğuna ekler."""
        with self._client_lock:
            if self._client_sock is None:
                return

        with self._queue_cond:
            if len(self._audio_queue) == self._audio_queue.maxlen:
                self._audio_queue.popleft()
                self._packets_dropped += 1
            self._audio_seq = (self._audio_seq + 1) & 0xFFFFFFFF
            self._audio_queue.append((self._audio_seq, pcm_bytes))
            self._queue_cond.notify()

    def get_stats(self) -> ServerStats:
        """Güncel bağlantı ve hız istatistiklerini döndürür."""
        with self._client_lock:
            connected = self._client_sock is not None
            client_addr = self._client_addr

        with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_rate_time
            if elapsed >= 1.0:
                self._kbps = (self._bytes_window * 8.0) / (elapsed * 1000.0)
                self._bytes_window = 0
                self._last_rate_time = now
            elif not connected:
                self._kbps = 0.0
            kbps = self._kbps

        transport_label = (
            ("Wi-Fi UDP+FEC" if self._udp_client_addr is not None else "Wi-Fi TCP+ADPCM")
            if self.mode == "wifi"
            else "USB PCM"
        )

        return ServerStats(
            running=self._server_sock is not None and not self._stop_event.is_set(),
            connected=connected,
            client_addr=client_addr,
            rtt_ms=self._rtt_ms if connected else None,
            kbps=kbps if connected else 0.0,
            packets_sent=self._packets_sent,
            packets_dropped=self._packets_dropped,
            transport_label=transport_label,
        )

    def _accept_loop(self) -> None:
        while not self._stop_event.is_set() and self._server_sock is not None:
            try:
                conn, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            self._attach_client(conn, f"{addr[0]}:{addr[1]}")

    def _attach_client(self, conn: socket.socket, addr_str: str) -> None:
        self._disconnect_active_client()

        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "SIO_KEEPALIVE_VALS"):
                try:
                    conn.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 5000, 1000))
                except OSError:
                    pass
            try:
                # DSCP EF (0xB8) — Wi-Fi WMM Voice düşük gecikme önceliği
                conn.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)
            except OSError:
                pass
            buf_size = 131072 if self.mode == "wifi" else 65536
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buf_size)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buf_size)
            conn.settimeout(1.0)
        except OSError:
            pass

        client_stop = threading.Event()
        with self._queue_cond:
            self._audio_queue.clear()
            self._ctrl_queue.clear()

        with self._rate_lock:
            self._bytes_window = 0
            self._last_rate_time = time.monotonic()
            self._kbps = 0.0

        with self._client_lock:
            self._client_sock = conn
            self._client_addr = addr_str
            self._udp_client_addr = None
            self._client_stop = client_stop
            self._rtt_ms = None

        self._adpcm_encoder.reset()
        self._prev_adpcm_frame = None

        sender = threading.Thread(
            target=self._sender_loop,
            args=(conn, client_stop),
            name="BTBridge-Sender",
            daemon=True,
        )
        receiver = threading.Thread(
            target=self._receiver_loop,
            args=(conn, client_stop, addr_str),
            name="BTBridge-Receiver",
            daemon=True,
        )
        with self._client_lock:
            self._client_threads = [sender, receiver]

        sender.start()
        receiver.start()
        self._log(f"Android istemcisi bağlandı: {addr_str}")

    def _disconnect_active_client(self) -> None:
        with self._client_lock:
            sock = self._client_sock
            stop_ev = self._client_stop
            threads = list(self._client_threads)
            self._client_sock = None
            self._client_addr = None
            self._udp_client_addr = None
            self._client_stop = None
            self._client_threads = []
        self._prev_adpcm_frame = None

        if stop_ev is not None:
            stop_ev.set()
        with self._queue_cond:
            self._queue_cond.notify_all()
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

        current = threading.current_thread()
        for t in threads:
            if t is not current and t.is_alive():
                t.join(timeout=1.5)

    def _enqueue_ctrl(self, packet: bytes) -> None:
        with self._queue_cond:
            self._ctrl_queue.append(packet)
            self._queue_cond.notify()

    def _send_all_cooperative(
        self,
        conn: socket.socket,
        data: bytes,
        client_stop: threading.Event,
        send_timeout: float = 8.0,
    ) -> None:
        view = memoryview(data)
        sent = 0
        total = len(data)
        last_progress = time.monotonic()
        while sent < total:
            if self._stop_event.is_set() or client_stop.is_set():
                raise ConnectionError("Gönderici durduruldu")
            try:
                _, writable, _ = select.select([], [conn], [], 0.5)
            except (OSError, ValueError) as exc:
                raise ConnectionError("Soket seçimi başarısız") from exc
            if not writable:
                if (time.monotonic() - last_progress) >= send_timeout:
                    raise TimeoutError("Gönderim zaman aşımı")
                continue
            try:
                chunk_sent = conn.send(view[sent:])
            except (BlockingIOError, socket.timeout):
                if (time.monotonic() - last_progress) >= send_timeout:
                    raise TimeoutError("Gönderim zaman aşımı")
                continue
            if chunk_sent <= 0:
                raise ConnectionError("Uzak soket bağlantısı kapandı")
            sent += chunk_sent
            last_progress = time.monotonic()

    def _udp_listener_loop(self) -> None:
        while not self._stop_event.is_set() and self._udp_sock is not None:
            try:
                data, addr = self._udp_sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break

            if len(data) < HEADER_SIZE:
                continue
            try:
                hdr = unpack_header(data[:HEADER_SIZE])
            except ValueError:
                continue
            if hdr.msg_type != MSG_UDP_HELLO:
                continue

            with self._client_lock:
                if self._client_sock is None or self._client_addr is None:
                    continue
                client_ip = self._client_addr.rsplit(":", 1)[0]
                if addr[0] != client_ip and client_ip != "127.0.0.1":
                    continue
                prev = self._udp_client_addr
                self._udp_client_addr = addr
            if prev is None:
                self._log(f"Wi-Fi UDP hızlı ses kanalı aktif (ADPCM + FEC): {addr[0]}:{addr[1]}")

    def _sender_loop(self, conn: socket.socket, client_stop: threading.Event) -> None:
        next_ping_at = time.monotonic()
        while not self._stop_event.is_set() and not client_stop.is_set():
            now = time.monotonic()
            if now >= next_ping_at:
                self._ping_seq = (self._ping_seq + 1) & 0xFFFFFFFF
                ping_pkt = pack_packet(MSG_PING, self._ping_seq, now_monotonic_ms())
                self._enqueue_ctrl(ping_pkt)
                next_ping_at = now + 1.0

            ctrl_batch: list[bytes] = []
            audio_items: list[tuple[int, bytes]] = []
            with self._queue_cond:
                if not self._ctrl_queue and not self._audio_queue and not client_stop.is_set():
                    self._queue_cond.wait(timeout=0.2)
                while self._ctrl_queue:
                    ctrl_batch.append(self._ctrl_queue.popleft())
                while self._audio_queue:
                    audio_items.append(self._audio_queue.popleft())

            if not ctrl_batch and not audio_items:
                continue

            tcp_batch: list[bytes] = list(ctrl_batch)
            udp_packets: list[bytes] = []
            udp_sock = self._udp_sock
            udp_addr = self._udp_client_addr

            for seq, pcm in audio_items:
                if self.mode == "wifi":
                    adpcm = self._adpcm_encoder.encode(pcm)
                    if udp_sock is not None and udp_addr is not None:
                        prev = self._prev_adpcm_frame if self._prev_adpcm_frame is not None else adpcm
                        udp_packets.append(
                            pack_packet(MSG_AUDIO_ADPCM_FEC, seq, now_monotonic_ms(), adpcm + prev)
                        )
                    else:
                        tcp_batch.append(pack_packet(MSG_AUDIO_ADPCM, seq, now_monotonic_ms(), adpcm))
                    self._prev_adpcm_frame = adpcm
                else:
                    tcp_batch.append(pack_packet(MSG_AUDIO, seq, now_monotonic_ms(), pcm))
                self._packets_sent += 1

            sent_bytes = 0
            if udp_packets and udp_sock is not None and udp_addr is not None:
                for pkt in udp_packets:
                    try:
                        udp_sock.sendto(pkt, udp_addr)
                        sent_bytes += len(pkt)
                    except OSError:
                        break

            if tcp_batch:
                payload = b"".join(tcp_batch)
                try:
                    self._send_all_cooperative(conn, payload, client_stop)
                    sent_bytes += len(payload)
                except (OSError, TimeoutError, ConnectionError):
                    client_stop.set()
                    break

            if sent_bytes > 0:
                with self._rate_lock:
                    self._bytes_window += sent_bytes

    def _receiver_loop(
        self,
        conn: socket.socket,
        client_stop: threading.Event,
        addr_str: str,
    ) -> None:
        while not self._stop_event.is_set() and not client_stop.is_set():
            try:
                raw_hdr = recv_exact(conn, HEADER_SIZE, stop_event=client_stop, idle_timeout=10.0)
                hdr = unpack_header(raw_hdr)
                if hdr.payload_len > 0:
                    _ = recv_exact(conn, hdr.payload_len, stop_event=client_stop, idle_timeout=10.0)
            except (ConnectionError, TimeoutError, OSError, ValueError):
                break

            if hdr.msg_type == MSG_PING:
                pong = pack_packet(MSG_PONG, hdr.seq, hdr.timestamp_ms)
                self._enqueue_ctrl(pong)
            elif hdr.msg_type == MSG_PONG:
                rtt = max(0, now_monotonic_ms() - hdr.timestamp_ms)
                self._rtt_ms = rtt

        client_stop.set()
        with self._client_lock:
            is_still_current = self._client_sock is conn
        if is_still_current:
            self._disconnect_active_client()
            self._log(f"İstemci bağlantısı kesildi: {addr_str}")
