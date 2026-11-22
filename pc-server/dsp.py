"""Gerçek zamanlı ses yeniden örnekleme, kanal eşleme ve 10 ms paketleme modülü."""

from __future__ import annotations

import math
import struct
import warnings
import numpy as np

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

from protocol import (
    ADPCM_CHANNEL_BYTES,
    ADPCM_FRAME_BYTES,
    ADPCM_STATE_BYTES,
    AUDIO_PAYLOAD_BYTES,
    FRAME_SAMPLES,
    SAMPLE_RATE,
)


def _rms_to_vu(rms: float, floor_db: float = -60.0) -> float:
    """RMS genliğini [0.0, 1.0] aralığında algısal VU seviyesine çevirir."""
    if rms <= 1e-7:
        return 0.0
    db = 20.0 * math.log10(min(rms, 1.0))
    if db <= floor_db:
        return 0.0
    return min(1.0, max(0.0, (db - floor_db) / (-floor_db)))


class AudioResamplerConverter:
    """Gelen ses akışını kesintisiz olarak 48 kHz / 16-bit Stereo LE PCM'e dönüştürür."""

    def __init__(
        self,
        src_rate: int,
        src_channels: int,
        src_format: str = "float32",
        dst_rate: int = SAMPLE_RATE,
    ) -> None:
        if src_rate <= 0 or dst_rate <= 0:
            raise ValueError("Örnekleme hızları pozitif olmalıdır")
        if src_channels < 1:
            raise ValueError("Kanal sayısı en az 1 olmalıdır")
        if src_format not in {"float32", "int16", "int32"}:
            raise ValueError(f"Desteklenmeyen kaynak biçimi: {src_format}")

        self.src_rate = int(src_rate)
        self.src_channels = int(src_channels)
        self.src_format = src_format
        self.dst_rate = int(dst_rate)

        self._step: float = float(self.src_rate) / float(self.dst_rate)
        self._pos: float = 1.0
        self._prev: np.ndarray = np.zeros((1, 2), dtype=np.float32)

    def reset(self) -> None:
        """Yeniden örnekleyici faz durumunu sıfırlar."""
        self._pos = 1.0
        self._prev.fill(0.0)

    def _decode_to_float32_stereo(self, raw_bytes: bytes) -> np.ndarray:
        if not raw_bytes:
            return np.empty((0, 2), dtype=np.float32)

        if self.src_format == "float32":
            arr = np.frombuffer(raw_bytes, dtype="<f4").astype(np.float32, copy=False)
        elif self.src_format == "int16":
            arr = np.frombuffer(raw_bytes, dtype="<i2").astype(np.float32) / 32768.0
        else:  # int32
            arr = np.frombuffer(raw_bytes, dtype="<i4").astype(np.float32) / 2147483648.0

        usable = (arr.size // self.src_channels) * self.src_channels
        if usable == 0:
            return np.empty((0, 2), dtype=np.float32)
        frames = arr[:usable].reshape(-1, self.src_channels)

        if self.src_channels == 1:
            return np.repeat(frames, 2, axis=1)
        if self.src_channels == 2:
            return np.ascontiguousarray(frames, dtype=np.float32)
        if self.src_channels >= 6:
            # 5.1 / 7.1 surround sinyali stereo L/R kanallarına indirger
            left = frames[:, 0] + 0.7071 * frames[:, 2] + 0.7071 * frames[:, 4]
            right = frames[:, 1] + 0.7071 * frames[:, 2] + 0.7071 * frames[:, 5]
            stereo = np.column_stack((left, right)).astype(np.float32)
            return np.clip(stereo, -1.0, 1.0)
        return np.ascontiguousarray(frames[:, :2], dtype=np.float32)

    def _resample_stereo(self, stereo: np.ndarray) -> np.ndarray:
        n = stereo.shape[0]
        if n == 0:
            return stereo
        if self.src_rate == self.dst_rate:
            return stereo

        buf = np.vstack((self._prev, stereo))
        if self._pos >= n:
            self._pos -= float(n)
            self._prev = buf[-1:].copy()
            return np.empty((0, 2), dtype=np.float32)

        count = int(math.ceil((float(n) - self._pos) / self._step))
        while count > 0 and (self._pos + (count - 1) * self._step) >= float(n):
            count -= 1

        if count <= 0:
            self._pos -= float(n)
            self._prev = buf[-1:].copy()
            return np.empty((0, 2), dtype=np.float32)

        positions = self._pos + np.arange(count, dtype=np.float64) * self._step
        idx = np.floor(positions).astype(np.intp)
        frac = (positions - idx).astype(np.float32)[:, np.newaxis]

        out = buf[idx] + frac * (buf[idx + 1] - buf[idx])

        next_pos = (self._pos + count * self._step) - float(n)
        self._pos = max(0.0, next_pos)
        self._prev = buf[-1:].copy()
        return out.astype(np.float32, copy=False)

    def process(self, raw_bytes: bytes) -> tuple[bytes, float, float]:
        """Ham ses bloğunu 48 kHz 16-bit LE Stereo PCM'e çevirir ve (pcm, vu_l, vu_r) döndürür."""
        stereo = self._decode_to_float32_stereo(raw_bytes)
        if stereo.shape[0] == 0:
            return b"", 0.0, 0.0

        resampled = self._resample_stereo(stereo)
        if resampled.shape[0] == 0:
            return b"", 0.0, 0.0

        rms_l = float(np.sqrt(np.mean(np.square(resampled[:, 0]), dtype=np.float64)))
        rms_r = float(np.sqrt(np.mean(np.square(resampled[:, 1]), dtype=np.float64)))
        vu_left = _rms_to_vu(rms_l)
        vu_right = _rms_to_vu(rms_r)

        clipped = np.clip(resampled, -1.0, 1.0)
        pcm_int16 = np.rint(clipped * 32767.0).astype("<i2")
        return pcm_int16.tobytes(), vu_left, vu_right


class FramePacketizer:
    """Değişken boyutlu PCM akışını tam 1920 baytlık (10 ms) karelere böler."""

    def __init__(self, frame_bytes: int = AUDIO_PAYLOAD_BYTES) -> None:
        if frame_bytes <= 0:
            raise ValueError("Kare boyutu pozitif olmalıdır")
        self.frame_bytes = frame_bytes
        self._buffer = bytearray()

    def push(self, pcm_bytes: bytes) -> list[bytes]:
        """Gelen baytları tampona ekler ve hazır tüm tam kareleri döndürür."""
        if not pcm_bytes:
            return []
        self._buffer.extend(pcm_bytes)
        frames: list[bytes] = []
        offset = 0
        total = len(self._buffer)
        while total - offset >= self.frame_bytes:
            frames.append(bytes(self._buffer[offset : offset + self.frame_bytes]))
            offset += self.frame_bytes
        if offset > 0:
            del self._buffer[:offset]
        return frames

    def reset(self) -> None:
        """Bekleyen yarım kare tamponunu temizler."""
        self._buffer.clear()


_ADPCM_STATE_STRUCT = struct.Struct("<hBhB")


class StereoImaAdpcmEncoder:
    """48 kHz 16-bit Stereo PCM karelerini 4:1 oranında 486 baytlık IMA ADPCM'e sıkıştırır."""

    def __init__(self) -> None:
        self._state_l: tuple[int, int] = (0, 0)
        self._state_r: tuple[int, int] = (0, 0)

    def reset(self) -> None:
        """Yeni akış için kodlayıcı tahmin durumunu sıfırlar."""
        self._state_l = (0, 0)
        self._state_r = (0, 0)

    def encode(self, pcm_bytes: bytes) -> bytes:
        """1920 baytlık stereo PCM karesini 486 baytlık kendi-kendine çözülebilir ADPCM'e çevirir."""
        if len(pcm_bytes) != AUDIO_PAYLOAD_BYTES:
            raise ValueError(
                f"Beklenen kare boyutu {AUDIO_PAYLOAD_BYTES} bayt, gelen: {len(pcm_bytes)}"
            )
        stereo = np.frombuffer(pcm_bytes, dtype="<i2").reshape(FRAME_SAMPLES, 2)
        left_raw = np.ascontiguousarray(stereo[:, 0]).tobytes()
        right_raw = np.ascontiguousarray(stereo[:, 1]).tobytes()

        pred_l, idx_l = self._state_l
        pred_r, idx_r = self._state_r
        header = _ADPCM_STATE_STRUCT.pack(pred_l, idx_l, pred_r, idx_r)

        enc_l, self._state_l = audioop.lin2adpcm(left_raw, 2, self._state_l)
        enc_r, self._state_r = audioop.lin2adpcm(right_raw, 2, self._state_r)
        return header + enc_l + enc_r


def decode_stereo_ima_adpcm(frame_bytes: bytes) -> bytes:
    """486 baytlık stereo IMA ADPCM karesini 1920 baytlık 16-bit LE Stereo PCM'e çözer."""
    if len(frame_bytes) != ADPCM_FRAME_BYTES:
        raise ValueError(
            f"Beklenen ADPCM kare boyutu {ADPCM_FRAME_BYTES} bayt, gelen: {len(frame_bytes)}"
        )
    pred_l, idx_l, pred_r, idx_r = _ADPCM_STATE_STRUCT.unpack_from(frame_bytes, 0)
    enc_l = frame_bytes[ADPCM_STATE_BYTES : ADPCM_STATE_BYTES + ADPCM_CHANNEL_BYTES]
    enc_r = frame_bytes[ADPCM_STATE_BYTES + ADPCM_CHANNEL_BYTES :]

    dec_l, _ = audioop.adpcm2lin(enc_l, 2, (pred_l, idx_l))
    dec_r, _ = audioop.adpcm2lin(enc_r, 2, (pred_r, idx_r))

    l_arr = np.frombuffer(dec_l, dtype="<i2")
    r_arr = np.frombuffer(dec_r, dtype="<i2")
    stereo = np.column_stack((l_arr, r_arr)).astype("<i2", copy=False)
    return stereo.tobytes()
