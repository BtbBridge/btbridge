package com.btbridge.app.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Process
import com.btbridge.app.protocol.BridgeProtocol
import kotlin.concurrent.thread

class LowLatencyAudioPlayer(
    private val jitterBuffer: JitterBuffer,
) {
    @Volatile
    private var running: Boolean = false
    private var playbackThread: Thread? = null

    @Volatile
    private var audioTrack: AudioTrack? = null

    fun start() {
        if (running) return
        val initialTrack = createAudioTrack()
        audioTrack = initialTrack
        running = true
        initialTrack.play()

        playbackThread = thread(start = true, name = "BTBridge-AudioOut") {
            try {
                Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO)
            } catch (_: Throwable) {
            }

            val frame = ByteArray(BridgeProtocol.FRAME_BYTES)
            val fadeTail = ByteArray(576) // 3 ms klik önleyici sönümleme
            var hadAudio = false
            var lastLeft: Short = 0
            var lastRight: Short = 0
            var track = initialTrack

            while (running) {
                if (jitterBuffer.read(frame, 0, frame.size)) {
                    if (jitterBuffer.consumeDiscontinuity()) {
                        val startL = if (hadAudio) lastLeft else 0
                        val startR = if (hadAudio) lastRight else 0
                        applySmoothJoin(frame, startL, startR, joinFrames = 144)
                    }
                    hadAudio = true
                    val len = frame.size
                    lastLeft = (((frame[len - 3].toInt() and 0xFF) shl 8) or (frame[len - 4].toInt() and 0xFF)).toShort()
                    lastRight = (((frame[len - 1].toInt() and 0xFF) shl 8) or (frame[len - 2].toInt() and 0xFF)).toShort()
                    val written = track.write(frame, 0, frame.size, AudioTrack.WRITE_BLOCKING)
                    if (written < 0) {
                        releaseTrackSafely(track)
                        if (!running) break
                        try {
                            Thread.sleep(40L)
                            val rebuilt = createAudioTrack()
                            audioTrack = rebuilt
                            track = rebuilt
                            track.play()
                            hadAudio = false
                            lastLeft = 0
                            lastRight = 0
                        } catch (_: Throwable) {
                            break
                        }
                    }
                } else {
                    if (hadAudio) {
                        hadAudio = false
                        fillFadeOut(fadeTail, lastLeft, lastRight)
                        track.write(fadeTail, 0, fadeTail.size, AudioTrack.WRITE_BLOCKING)
                        lastLeft = 0
                        lastRight = 0
                    }
                    jitterBuffer.waitForData(4L)
                }
            }
        }
    }

    fun stop() {
        running = false
        playbackThread?.interrupt()
        try {
            playbackThread?.join(500L)
        } catch (_: InterruptedException) {
        }
        playbackThread = null

        val track = audioTrack
        audioTrack = null
        if (track != null) {
            releaseTrackSafely(track)
        }
    }

    private fun releaseTrackSafely(track: AudioTrack) {
        try {
            if (track.playState == AudioTrack.PLAYSTATE_PLAYING) {
                track.pause()
            }
            track.flush()
            track.release()
        } catch (_: Throwable) {
        }
    }

    private fun createAudioTrack(): AudioTrack {
        val minBuf = AudioTrack.getMinBufferSize(
            BridgeProtocol.SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_STEREO,
            AudioFormat.ENCODING_PCM_16BIT,
        ).coerceAtLeast(BridgeProtocol.FRAME_BYTES)

        val targetBuf = maxOf(minBuf, BridgeProtocol.FRAME_BYTES * 3)
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
            .build()
        val format = AudioFormat.Builder()
            .setSampleRate(BridgeProtocol.SAMPLE_RATE)
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
            .build()

        return try {
            AudioTrack.Builder()
                .setAudioAttributes(attributes)
                .setAudioFormat(format)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY)
                .setBufferSizeInBytes(targetBuf)
                .build()
        } catch (_: UnsupportedOperationException) {
            AudioTrack.Builder()
                .setAudioAttributes(attributes)
                .setAudioFormat(format)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setBufferSizeInBytes(targetBuf)
                .build()
        }
    }

    private fun applySmoothJoin(
        frame: ByteArray,
        fromLeft: Short,
        fromRight: Short,
        joinFrames: Int,
    ) {
        val count = minOf(joinFrames, frame.size / 4)
        for (i in 0 until count) {
            val idx = i * 4
            val curL = (((frame[idx + 1].toInt() and 0xFF) shl 8) or (frame[idx].toInt() and 0xFF)).toShort()
            val curR = (((frame[idx + 3].toInt() and 0xFF) shl 8) or (frame[idx + 2].toInt() and 0xFF)).toShort()
            val alpha = (i + 1).toFloat() / count.toFloat()
            val mixL = (fromLeft * (1.0f - alpha) + curL * alpha).toInt().coerceIn(-32768, 32767)
            val mixR = (fromRight * (1.0f - alpha) + curR * alpha).toInt().coerceIn(-32768, 32767)
            frame[idx] = (mixL and 0xFF).toByte()
            frame[idx + 1] = ((mixL ushr 8) and 0xFF).toByte()
            frame[idx + 2] = (mixR and 0xFF).toByte()
            frame[idx + 3] = ((mixR ushr 8) and 0xFF).toByte()
        }
    }

    private fun fillFadeOut(buf: ByteArray, startLeft: Short, startRight: Short) {
        val frames = buf.size / 4
        for (i in 0 until frames) {
            val gain = 1.0f - (i + 1).toFloat() / frames.toFloat()
            val l = (startLeft * gain).toInt().toShort()
            val r = (startRight * gain).toInt().toShort()
            val idx = i * 4
            buf[idx] = (l.toInt() and 0xFF).toByte()
            buf[idx + 1] = ((l.toInt() ushr 8) and 0xFF).toByte()
            buf[idx + 2] = (r.toInt() and 0xFF).toByte()
            buf[idx + 3] = ((r.toInt() ushr 8) and 0xFF).toByte()
        }
    }
}
