package com.btbridge.app.protocol

/**
 * CPython `audioop.lin2adpcm` (16-bit Stereo) ile bit-birebir uyumlu sıfır-ayırmalı IMA ADPCM çözücü.
 */
object ImaAdpcmDecoder {
    private val INDEX_TABLE = intArrayOf(
        -1, -1, -1, -1, 2, 4, 6, 8,
        -1, -1, -1, -1, 2, 4, 6, 8,
    )

    private val STEPSIZE_TABLE = intArrayOf(
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
        50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
        337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
        2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
        15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
    )

    fun decodeFrame(src: ByteArray, srcOffset: Int, dstPcm: ByteArray): Boolean {
        if (srcOffset < 0 || srcOffset + BridgeProtocol.ADPCM_FRAME_BYTES > src.size) {
            return false
        }
        if (dstPcm.size < BridgeProtocol.FRAME_BYTES) {
            return false
        }

        // <hBhB (6 byte): predL (int16 LE), idxL (uint8), predR (int16 LE), idxR (uint8)
        val predL = (((src[srcOffset + 1].toInt() and 0xFF) shl 8) or (src[srcOffset].toInt() and 0xFF)).toShort().toInt()
        val idxL = (src[srcOffset + 2].toInt() and 0xFF).coerceIn(0, 88)
        val predR = (((src[srcOffset + 4].toInt() and 0xFF) shl 8) or (src[srcOffset + 3].toInt() and 0xFF)).toShort().toInt()
        val idxR = (src[srcOffset + 5].toInt() and 0xFF).coerceIn(0, 88)

        val leftOffset = srcOffset + BridgeProtocol.ADPCM_STATE_BYTES
        val rightOffset = leftOffset + BridgeProtocol.ADPCM_CHANNEL_BYTES

        decodeChannel(src, leftOffset, BridgeProtocol.ADPCM_CHANNEL_BYTES, predL, idxL, dstPcm, 0)
        decodeChannel(src, rightOffset, BridgeProtocol.ADPCM_CHANNEL_BYTES, predR, idxR, dstPcm, 2)
        return true
    }

    private fun decodeChannel(
        src: ByteArray,
        srcStart: Int,
        byteCount: Int,
        initialPred: Int,
        initialIndex: Int,
        dstPcm: ByteArray,
        dstChannelOffset: Int,
    ) {
        var valpred = initialPred
        var index = initialIndex
        var step = STEPSIZE_TABLE[index]
        var dstIdx = dstChannelOffset

        for (i in 0 until byteCount) {
            val packed = src[srcStart + i].toInt() and 0xFF

            // 1. Yüksek nibble
            val deltaHi = (packed ushr 4) and 0xF
            index = (index + INDEX_TABLE[deltaHi]).coerceIn(0, 88)
            var vpdiffHi = step ushr 3
            if ((deltaHi and 4) != 0) vpdiffHi += step
            if ((deltaHi and 2) != 0) vpdiffHi += step ushr 1
            if ((deltaHi and 1) != 0) vpdiffHi += step ushr 2
            valpred = if ((deltaHi and 8) != 0) valpred - vpdiffHi else valpred + vpdiffHi
            if (valpred > 32767) valpred = 32767 else if (valpred < -32768) valpred = -32768
            step = STEPSIZE_TABLE[index]
            dstPcm[dstIdx] = (valpred and 0xFF).toByte()
            dstPcm[dstIdx + 1] = ((valpred ushr 8) and 0xFF).toByte()
            dstIdx += 4

            // 2. Düşük nibble
            val deltaLo = packed and 0xF
            index = (index + INDEX_TABLE[deltaLo]).coerceIn(0, 88)
            var vpdiffLo = step ushr 3
            if ((deltaLo and 4) != 0) vpdiffLo += step
            if ((deltaLo and 2) != 0) vpdiffLo += step ushr 1
            if ((deltaLo and 1) != 0) vpdiffLo += step ushr 2
            valpred = if ((deltaLo and 8) != 0) valpred - vpdiffLo else valpred + vpdiffLo
            if (valpred > 32767) valpred = 32767 else if (valpred < -32768) valpred = -32768
            step = STEPSIZE_TABLE[index]
            dstPcm[dstIdx] = (valpred and 0xFF).toByte()
            dstPcm[dstIdx + 1] = ((valpred ushr 8) and 0xFF).toByte()
            dstIdx += 4
        }
    }
}
