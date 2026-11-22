package com.btbridge.app.audio

import android.os.SystemClock
import com.btbridge.app.protocol.BridgeProtocol

enum class JitterProfile(
    val id: String,
    val label: String,
    val targetMs: Int,
    val maxMs: Int,
) {
    ULTRA_LOW("ultra_low", "Ultra Düşük (~20ms)", 20, 60),
    BALANCED("balanced", "Dengeli (~40ms)", 40, 120),
    STABLE("stable", "Kararlı (~80ms)", 80, 200),
    WIFI_SAFE("wifi_safe", "Wi-Fi Ekstra Kararlı (~140ms)", 140, 320);

    companion object {
        fun fromId(id: String?): JitterProfile =
            entries.firstOrNull { it.id == id } ?: BALANCED
    }
}

class JitterBuffer(
    initialProfile: JitterProfile = JitterProfile.BALANCED,
) {
    companion object {
        // 48000 Hz * 2 ch * 2 bytes = 192000 bytes/s -> 192 bytes/ms
        const val BYTES_PER_MS: Int = 192
        private const val FRAME_ALIGN: Int = 4
        private const val CAPACITY: Int = 192000 // 1000 ms
    }

    @Suppress("PLATFORM_CLASS_MAPPED_TO_KOTLIN")
    private val lock = Object()
    private val ring = ByteArray(CAPACITY)
    private var readPos: Int = 0
    private var writePos: Int = 0
    private var size: Int = 0
    private var priming: Boolean = true
    private var discontinuity: Boolean = false

    @Volatile
    var profile: JitterProfile = initialProfile
        private set

    private var isWifiMode: Boolean = false
    private var adaptiveExtraMs: Int = 0
    private var lastUnderrunMs: Long = 0L
    private var lastAdaptiveStepMs: Long = 0L

    private var targetBytes: Int = align4(initialProfile.targetMs * BYTES_PER_MS)
    private var maxBytes: Int = align4(initialProfile.maxMs * BYTES_PER_MS)
    private var primingThresholdBytes: Int = targetBytes

    @Volatile
    var droppedBytes: Long = 0L
        private set

    private fun align4(value: Int): Int = (value / FRAME_ALIGN) * FRAME_ALIGN

    private fun recomputeBoundsLocked() {
        val baseTargetMs = if (isWifiMode) maxOf(profile.targetMs, 60) else profile.targetMs
        val baseMaxMs = if (isWifiMode) maxOf(profile.maxMs, 180) else profile.maxMs
        val effTargetMs = (baseTargetMs + adaptiveExtraMs).coerceAtMost(350)
        val effMaxMs = maxOf(baseMaxMs + adaptiveExtraMs, effTargetMs + 100).coerceAtMost(600)
        targetBytes = align4(effTargetMs * BYTES_PER_MS)
        maxBytes = align4(effMaxMs * BYTES_PER_MS)
        if (priming) {
            primingThresholdBytes = minOf(primingThresholdBytes, targetBytes)
        }
    }

    private fun trimTargetLocked(): Int =
        minOf(maxBytes - BridgeProtocol.FRAME_BYTES, targetBytes + BridgeProtocol.FRAME_BYTES)
            .coerceAtLeast(targetBytes)

    fun setNetworkMode(wifi: Boolean) {
        synchronized(lock) {
            isWifiMode = wifi
            adaptiveExtraMs = 0
            lastUnderrunMs = 0L
            lastAdaptiveStepMs = 0L
            recomputeBoundsLocked()
            if (priming) {
                primingThresholdBytes = targetBytes
            }
            lock.notifyAll()
        }
    }

    fun setProfile(newProfile: JitterProfile) {
        synchronized(lock) {
            profile = newProfile
            adaptiveExtraMs = 0
            recomputeBoundsLocked()
            if (size > maxBytes) {
                val excess = align4(size - trimTargetLocked())
                if (excess > 0) {
                    discardOldestLocked(excess)
                }
            }
            lock.notifyAll()
        }
    }

    fun clear() {
        synchronized(lock) {
            readPos = 0
            writePos = 0
            size = 0
            priming = true
            discontinuity = false
            recomputeBoundsLocked()
            primingThresholdBytes = targetBytes
            lock.notifyAll()
        }
    }

    fun consumeDiscontinuity(): Boolean = synchronized(lock) {
        val flag = discontinuity
        discontinuity = false
        flag
    }

    fun write(data: ByteArray, offset: Int = 0, length: Int = data.size) {
        if (length <= 0) return
        val alignedLen = align4(length).coerceAtMost(CAPACITY)
        if (alignedLen <= 0) return

        synchronized(lock) {
            if (isWifiMode && adaptiveExtraMs > 0) {
                val now = safeElapsedMs()
                if (lastAdaptiveStepMs > 0L && (now - lastAdaptiveStepMs) >= 25000L && (now - lastUnderrunMs) >= 25000L) {
                    adaptiveExtraMs = (adaptiveExtraMs - 10).coerceAtLeast(0)
                    lastAdaptiveStepMs = now
                    recomputeBoundsLocked()
                }
            }

            if (size + alignedLen > CAPACITY) {
                val needed = align4(size + alignedLen - CAPACITY + (FRAME_ALIGN - 1))
                discardOldestLocked(needed.coerceAtMost(size))
            }

            val firstChunk = minOf(alignedLen, CAPACITY - writePos)
            System.arraycopy(data, offset, ring, writePos, firstChunk)
            val remaining = alignedLen - firstChunk
            if (remaining > 0) {
                System.arraycopy(data, offset + firstChunk, ring, 0, remaining)
            }
            writePos = (writePos + alignedLen) % CAPACITY
            size += alignedLen

            // Gecikme birikmesini önlemek için maxBytes sınırı aşılırsa eski örnekleri at
            if (size > maxBytes) {
                val trim = align4(size - trimTargetLocked())
                if (trim > 0) {
                    discardOldestLocked(trim)
                }
            }
            lock.notifyAll()
        }
    }

    fun waitForData(timeoutMs: Long) {
        if (timeoutMs <= 0L) return
        synchronized(lock) {
            if (size == 0 || (priming && size < primingThresholdBytes)) {
                try {
                    lock.wait(timeoutMs)
                } catch (_: InterruptedException) {
                    Thread.currentThread().interrupt()
                }
            }
        }
    }

    fun read(dest: ByteArray, offset: Int = 0, length: Int = dest.size): Boolean {
        if (length <= 0) return false
        synchronized(lock) {
            if (priming) {
                if (size < primingThresholdBytes) {
                    return false
                }
                priming = false
            }

            if (size < length) {
                priming = true
                discontinuity = true
                if (isWifiMode) {
                    val now = safeElapsedMs()
                    if (lastUnderrunMs > 0L && (now - lastUnderrunMs) < 6000L && adaptiveExtraMs < 100) {
                        adaptiveExtraMs = (adaptiveExtraMs + 20).coerceAtMost(100)
                        lastAdaptiveStepMs = now
                        recomputeBoundsLocked()
                    }
                    lastUnderrunMs = now
                    primingThresholdBytes = targetBytes
                } else {
                    primingThresholdBytes = maxOf(BridgeProtocol.FRAME_BYTES, targetBytes / 2)
                }
                return false
            }

            val firstChunk = minOf(length, CAPACITY - readPos)
            System.arraycopy(ring, readPos, dest, offset, firstChunk)
            val remaining = length - firstChunk
            if (remaining > 0) {
                System.arraycopy(ring, 0, dest, offset + firstChunk, remaining)
            }
            readPos = (readPos + length) % CAPACITY
            size -= length
            return true
        }
    }

    fun bufferedMs(): Int = synchronized(lock) { size / BYTES_PER_MS }

    fun bufferedBytes(): Int = synchronized(lock) { size }

    fun currentTargetMs(): Int = synchronized(lock) { targetBytes / BYTES_PER_MS }

    private fun discardOldestLocked(bytesToDrop: Int) {
        val drop = align4(bytesToDrop).coerceAtMost(size)
        if (drop <= 0) return
        readPos = (readPos + drop) % CAPACITY
        size -= drop
        droppedBytes += drop
        discontinuity = true
    }

    private fun safeElapsedMs(): Long = try {
        SystemClock.elapsedRealtime()
    } catch (_: Throwable) {
        // JVM birim test ortamı
        System.nanoTime() / 1_000_000L
    }
}
