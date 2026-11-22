package com.btbridge.app

import com.btbridge.app.protocol.BridgeProtocol
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BridgeProtocolTest {

    @Test
    fun encodeAndDecodeHeaderRoundtrip() {
        val buf = ByteArray(BridgeProtocol.HEADER_SIZE)
        val seq = 0x12345678L
        val ts = 987654321012L
        BridgeProtocol.encodeHeader(buf, BridgeProtocol.TYPE_AUDIO, seq, ts, 1920)

        val decoded = BridgeProtocol.PacketHeader()
        assertTrue(BridgeProtocol.decodeHeader(buf, decoded))
        assertEquals(BridgeProtocol.TYPE_AUDIO, decoded.type)
        assertEquals(seq, decoded.seq)
        assertEquals(ts, decoded.timestampMs)
        assertEquals(1920, decoded.payloadLen)
    }

    @Test
    fun decodeRejectsInvalidMagicOrOversizePayload() {
        val buf = ByteArray(BridgeProtocol.HEADER_SIZE)
        BridgeProtocol.encodeHeader(buf, BridgeProtocol.TYPE_PING, 1L, 100L, 0)
        buf[0] = 0x00

        val out = BridgeProtocol.PacketHeader()
        assertFalse(BridgeProtocol.decodeHeader(buf, out))

        BridgeProtocol.encodeHeader(buf, BridgeProtocol.TYPE_AUDIO, 1L, 100L, BridgeProtocol.MAX_PAYLOAD_LEN)
        // Payload length alanını MAX_PAYLOAD_LEN + 1 yap
        buf[15] = 0x7F
        buf[16] = 0xFF.toByte()
        assertFalse(BridgeProtocol.decodeHeader(buf, out))
    }
}
