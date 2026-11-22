"""BTBridge DSP (yeniden örnekleme, kanal eşleme, VU ve paketleme) testleri."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

PC_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(PC_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PC_SERVER_DIR))

from dsp import (  # noqa: E402
    AudioResamplerConverter,
    FramePacketizer,
    StereoImaAdpcmEncoder,
    decode_stereo_ima_adpcm,
)
from protocol import ADPCM_FRAME_BYTES, AUDIO_PAYLOAD_BYTES  # noqa: E402


def test_48k_float32_stereo_and_clipping() -> None:
    conv = AudioResamplerConverter(src_rate=48000, src_channels=2, src_format="float32")
    raw = np.array(
        [
            [0.0, 0.0],
            [0.5, -0.5],
            [1.5, -1.8],  # Kırpma (clipping) sınırı
        ],
        dtype="<f4",
    ).tobytes()

    pcm_bytes, vu_l, vu_r = conv.process(raw)
    out = np.frombuffer(pcm_bytes, dtype="<i2").reshape(-1, 2)
    assert out.shape == (3, 2)
    assert out[0, 0] == 0 and out[0, 1] == 0
    assert abs(int(out[1, 0]) - 16384) <= 1
    assert abs(int(out[1, 1]) + 16384) <= 1
    assert out[2, 0] == 32767
    assert out[2, 1] == -32767
    assert 0.8 <= vu_l <= 1.0
    assert 0.8 <= vu_r <= 1.0


def test_44100_to_48000_streaming_sine_continuity() -> None:
    src_rate = 44100
    dst_rate = 48000
    freq_hz = 1000.0
    conv = AudioResamplerConverter(src_rate=src_rate, src_channels=2, src_format="float32", dst_rate=dst_rate)
    packetizer = FramePacketizer()

    # 1.0 saniyelik 44.1 kHz sinüsü 10 ms'lik (441 örnek) parçalar halinde akıt
    t = np.arange(src_rate, dtype=np.float64) / src_rate
    sine = (0.6 * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    stereo = np.column_stack((sine, -sine)).astype("<f4")

    all_pcm = bytearray()
    frames_out: list[bytes] = []
    chunk_size = 441
    for idx in range(0, src_rate, chunk_size):
        chunk = stereo[idx : idx + chunk_size].tobytes()
        pcm, _vl, _vr = conv.process(chunk)
        all_pcm.extend(pcm)
        frames_out.extend(packetizer.push(pcm))

    samples = np.frombuffer(bytes(all_pcm), dtype="<i2").reshape(-1, 2)
    # 1 saniyelik çıktı yaklaşık 48000 stereo kare olmalı
    assert 47995 <= samples.shape[0] <= 48005
    assert all(len(f) == AUDIO_PAYLOAD_BYTES for f in frames_out)
    assert len(frames_out) >= 99

    # FFT ile temel frekansın 1000 Hz'de korunduğunu doğrula
    left_float = samples[:, 0].astype(np.float64) / 32768.0
    freqs = np.fft.rfftfreq(left_float.size, d=1.0 / dst_rate)
    mags = np.abs(np.fft.rfft(left_float))
    peak_freq = freqs[int(np.argmax(mags))]
    assert abs(peak_freq - freq_hz) <= 3.0

    # Parça sınırlarında ani tıklama / sıçrama olmadığını doğrula
    max_step = np.max(np.abs(np.diff(left_float)))
    expected_step = 0.6 * (2.0 * np.pi * freq_hz / dst_rate)
    assert max_step < expected_step * 1.25


def test_96k_downsampling_and_multichannel_mapping() -> None:
    # 96 kHz -> 48 kHz
    conv_96 = AudioResamplerConverter(src_rate=96000, src_channels=2, src_format="int16")
    t = np.arange(960, dtype=np.float64) / 96000.0
    sig = (np.sin(2.0 * np.pi * 500.0 * t) * 16000.0).astype("<i2")
    raw_stereo = np.column_stack((sig, sig)).tobytes()
    pcm_96, _, _ = conv_96.process(raw_stereo)
    out_96 = np.frombuffer(pcm_96, dtype="<i2").reshape(-1, 2)
    assert 478 <= out_96.shape[0] <= 482

    # Mono -> Stereo
    conv_mono = AudioResamplerConverter(src_rate=48000, src_channels=1, src_format="float32")
    raw_mono = np.array([0.25, -0.5, 0.75], dtype="<f4").tobytes()
    pcm_mono, _, _ = conv_mono.process(raw_mono)
    out_mono = np.frombuffer(pcm_mono, dtype="<i2").reshape(-1, 2)
    assert out_mono.shape == (3, 2)
    assert np.array_equal(out_mono[:, 0], out_mono[:, 1])

    # 6 Kanal (5.1) -> Stereo
    conv_51 = AudioResamplerConverter(src_rate=48000, src_channels=6, src_format="float32")
    raw_51 = np.array([[0.4, 0.2, 0.1, 0.0, 0.1, 0.1]], dtype="<f4").tobytes()
    pcm_51, _, _ = conv_51.process(raw_51)
    out_51 = np.frombuffer(pcm_51, dtype="<i2").reshape(-1, 2)
    assert out_51.shape == (1, 2)
    assert out_51[0, 0] > out_51[0, 1] > 0


def test_vu_silence_and_packetizer_irregular_chunks() -> None:
    conv = AudioResamplerConverter(src_rate=48000, src_channels=2, src_format="float32")
    silence = np.zeros((480, 2), dtype="<f4").tobytes()
    _pcm, vu_l, vu_r = conv.process(silence)
    assert vu_l == 0.0 and vu_r == 0.0

    pkt = FramePacketizer(frame_bytes=AUDIO_PAYLOAD_BYTES)
    assert pkt.push(b"\x00" * 1000) == []
    frames = pkt.push(b"\x11" * 3000)  # Toplam 4000 -> 2 kare (3840) + 160 kalan
    assert len(frames) == 2
    assert all(len(f) == AUDIO_PAYLOAD_BYTES for f in frames)
    frames2 = pkt.push(b"\x22" * 1760)  # 160 + 1760 = 1920 -> 1 kare
    assert len(frames2) == 1
    assert frames2[0].startswith(b"\x11" * 160)
    assert frames2[0].endswith(b"\x22" * 1760)


def test_stereo_ima_adpcm_roundtrip_snr_and_channel_separation() -> None:
    enc = StereoImaAdpcmEncoder()
    t = np.arange(4800, dtype=np.float64) / 48000.0
    left = np.rint(0.55 * np.sin(2.0 * np.pi * 440.0 * t) * 32767.0).astype("<i2")
    right = np.rint(0.35 * np.cos(2.0 * np.pi * 880.0 * t) * 32767.0).astype("<i2")
    raw = np.column_stack((left, right)).astype("<i2").tobytes()

    dec_chunks: list[np.ndarray] = []
    for offset in range(0, len(raw), AUDIO_PAYLOAD_BYTES):
        chunk = raw[offset : offset + AUDIO_PAYLOAD_BYTES]
        adpcm = enc.encode(chunk)
        assert len(adpcm) == ADPCM_FRAME_BYTES
        dec_pcm = decode_stereo_ima_adpcm(adpcm)
        assert len(dec_pcm) == AUDIO_PAYLOAD_BYTES
        dec_chunks.append(np.frombuffer(dec_pcm, dtype="<i2").reshape(-1, 2))

    dec_all = np.vstack(dec_chunks)
    # İlk ısınma karesinden sonra SNR > 30 dB ve L/R kanalları ayrık olmalı
    ref_l = left[480:].astype(np.float64)
    out_l = dec_all[480:, 0].astype(np.float64)
    snr_l = 10.0 * np.log10(np.mean(ref_l**2) / max(np.mean((ref_l - out_l) ** 2), 1e-9))
    assert snr_l > 30.0

    ref_r = right[480:].astype(np.float64)
    out_r = dec_all[480:, 1].astype(np.float64)
    snr_r = 10.0 * np.log10(np.mean(ref_r**2) / max(np.mean((ref_r - out_r) ** 2), 1e-9))
    assert snr_r > 30.0
    assert not np.array_equal(dec_all[:, 0], dec_all[:, 1])
