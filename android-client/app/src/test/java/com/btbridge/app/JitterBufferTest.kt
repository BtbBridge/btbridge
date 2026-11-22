package com.btbridge.app

import com.btbridge.app.audio.JitterBuffer
import com.btbridge.app.audio.JitterProfile
import com.btbridge.app.protocol.BridgeProtocol
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class JitterBufferTest {

    @Test
    fun primingHoldsUntilTargetReachedAndReadsInOrder() {
        val jb = JitterBuffer(JitterProfile.ULTRA_LOW) // target = 20ms (2 kare)
        val f1 = ByteArray(BridgeProtocol.FRAME_BYTES) { 1 }
        val f2 = ByteArray(BridgeProtocol.FRAME_BYTES) { 2 }
        val out = ByteArray(BridgeProtocol.FRAME_BYTES)

        jb.write(f1)
        assertFalse(jb.read(out)) // Henüz 10ms var (< 20ms hedef)

        jb.write(f2)
        assertTrue(jb.read(out))
        assertArrayEquals(f1, out)

        assertTrue(jb.read(out))
        assertArrayEquals(f2, out)

        assertFalse(jb.read(out)) // Underrun sonrası tekrar priming
    }

    @Test
    fun overflowTrimsOldestFramesToKeepLatencyBounded() {
        val jb = JitterBuffer(JitterProfile.ULTRA_LOW) // max = 60ms -> 11520B
        val frame = ByteArray(BridgeProtocol.FRAME_BYTES) { 7 }

        repeat(7) { // 70ms yaz -> 60ms sınırını aşınca 30ms tampon hedefine kırpar
            jb.write(frame)
        }

        assertTrue(jb.droppedBytes > 0L)
        assertEquals(30, jb.bufferedMs())

        repeat(2) { // 20ms daha ekleyince 50ms olur (<= maxMs)
            jb.write(frame)
        }
        assertEquals(50, jb.bufferedMs())
        assertTrue(jb.bufferedMs() <= JitterProfile.ULTRA_LOW.maxMs)
        assertTrue(jb.consumeDiscontinuity())
        assertFalse(jb.consumeDiscontinuity())
    }

    @Test
    fun wifiModeEnforcesMinimumSafeTargetAndSupportsWifiSafeProfile() {
        val jb = JitterBuffer(JitterProfile.ULTRA_LOW)
        jb.setNetworkMode(true)
        assertTrue(jb.currentTargetMs() >= 60)

        jb.setProfile(JitterProfile.WIFI_SAFE)
        assertEquals(140, jb.currentTargetMs())
    }
}
