package com.btbridge.app.protocol

import java.io.EOFException
import java.io.InputStream

object BridgeProtocol {
    const val MAGIC: Int = 0xB7B7

    const val TYPE_AUDIO: Byte = 1
    const val TYPE_PING: Byte = 2
    const val TYPE_PONG: Byte = 3
    const val TYPE_AUDIO_ADPCM: Byte = 4
    const val TYPE_UDP_HELLO: Byte = 5
    const val TYPE_AUDIO_ADPCM_FEC: Byte = 6

    const val HEADER_SIZE: Int = 17
    const val MAX_PAYLOAD_LEN: Int = 8192

    const val SAMPLE_RATE: Int = 48000
    const val CHANNELS: Int = 2
    const val FRAME_MS: Int = 10
    const val FRAME_BYTES: Int = 1920
    const val ADPCM_STATE_BYTES: Int = 6
    const val ADPCM_CHANNEL_BYTES: Int = 240
    const val ADPCM_FRAME_BYTES: Int = 486
    const val ADPCM_FEC_BYTES: Int = 972
    const val DEFAULT_PORT: Int = 50005

    data class PacketHeader(
        var type: Byte = 0,
        var seq: Long = 0L,
        var timestampMs: Long = 0L,
        var payloadLen: Int = 0,
    )

    fun encodeHeader(
        buffer: ByteArray,
        type: Byte,
        seq: Long,
        timestampMs: Long,
        payloadLen: Int,
    ) {
        require(buffer.size >= HEADER_SIZE) { "Buffer size must be >= $HEADER_SIZE" }
        require(payloadLen in 0..MAX_PAYLOAD_LEN) { "Invalid payload length: $payloadLen" }

        buffer[0] = ((MAGIC ushr 8) and 0xFF).toByte()
        buffer[1] = (MAGIC and 0xFF).toByte()
        buffer[2] = type

        buffer[3] = ((seq ushr 24) and 0xFF).toByte()
        buffer[4] = ((seq ushr 16) and 0xFF).toByte()
        buffer[5] = ((seq ushr 8) and 0xFF).toByte()
        buffer[6] = (seq and 0xFF).toByte()

        buffer[7] = ((timestampMs ushr 56) and 0xFF).toByte()
        buffer[8] = ((timestampMs ushr 48) and 0xFF).toByte()
        buffer[9] = ((timestampMs ushr 40) and 0xFF).toByte()
        buffer[10] = ((timestampMs ushr 32) and 0xFF).toByte()
        buffer[11] = ((timestampMs ushr 24) and 0xFF).toByte()
        buffer[12] = ((timestampMs ushr 16) and 0xFF).toByte()
        buffer[13] = ((timestampMs ushr 8) and 0xFF).toByte()
        buffer[14] = (timestampMs and 0xFF).toByte()

        buffer[15] = ((payloadLen ushr 8) and 0xFF).toByte()
        buffer[16] = (payloadLen and 0xFF).toByte()
    }

    fun decodeHeader(buffer: ByteArray, out: PacketHeader): Boolean {
        if (buffer.size < HEADER_SIZE) return false

        val magic = ((buffer[0].toInt() and 0xFF) shl 8) or (buffer[1].toInt() and 0xFF)
        if (magic != MAGIC) return false

        val type = buffer[2]
        if (type != TYPE_AUDIO &&
            type != TYPE_PING &&
            type != TYPE_PONG &&
            type != TYPE_AUDIO_ADPCM &&
            type != TYPE_UDP_HELLO &&
            type != TYPE_AUDIO_ADPCM_FEC
        ) {
            return false
        }

        val seq = ((buffer[3].toLong() and 0xFFL) shl 24) or
            ((buffer[4].toLong() and 0xFFL) shl 16) or
            ((buffer[5].toLong() and 0xFFL) shl 8) or
            (buffer[6].toLong() and 0xFFL)

        val timestampMs = ((buffer[7].toLong() and 0xFFL) shl 56) or
            ((buffer[8].toLong() and 0xFFL) shl 48) or
            ((buffer[9].toLong() and 0xFFL) shl 40) or
            ((buffer[10].toLong() and 0xFFL) shl 32) or
            ((buffer[11].toLong() and 0xFFL) shl 24) or
            ((buffer[12].toLong() and 0xFFL) shl 16) or
            ((buffer[13].toLong() and 0xFFL) shl 8) or
            (buffer[14].toLong() and 0xFFL)

        val payloadLen = ((buffer[15].toInt() and 0xFF) shl 8) or (buffer[16].toInt() and 0xFF)
        if (payloadLen > MAX_PAYLOAD_LEN) return false

        out.type = type
        out.seq = seq
        out.timestampMs = timestampMs
        out.payloadLen = payloadLen
        return true
    }

    fun readFully(input: InputStream, dest: ByteArray, length: Int) {
        var totalRead = 0
        while (totalRead < length) {
            val count = input.read(dest, totalRead, length - totalRead)
            if (count < 0) {
                throw EOFException("Socket closed while reading $length bytes")
            }
            totalRead += count
        }
    }
}
