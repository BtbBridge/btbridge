package com.btbridge.app

import com.btbridge.app.protocol.BridgeProtocol
import com.btbridge.app.protocol.ImaAdpcmDecoder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ImaAdpcmDecoderTest {

    private fun hexToBytes(hex: String): ByteArray {
        val len = hex.length / 2
        val out = ByteArray(len)
        for (i in 0 until len) {
            out[i] = hex.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
        return out
    }

    private fun readLeShort(pcm: ByteArray, sampleIndex: Int): Int {
        val idx = sampleIndex * 2
        return (((pcm[idx + 1].toInt() and 0xFF) shl 8) or (pcm[idx].toInt() and 0xFF)).toShort().toInt()
    }

    @Test
    fun decodesPythonAudioopFramesBitExactly() {
        val a1 = hexToBytes(
            "000000000000077777777401010101101101000080999bbcbdbdbbccbbcbcbcbbcbcbbbcbbbcbbbcbabbbbbbbbaa998" +
                "113454435343443433443335234333433423423233422322221200099bcdbdbccbccbbccbbcbbdacabbbcbbcbbbbcbb" +
                "bbcababaaa999001236353534344335334334424233343343242333333334222120188abcccccbccbcbcbcbcbcbbcbb" +
                "cbbcbbcbbbcabbcaabababa9a99801244354434344334433434334342343242333334333233332311188abdccccbccb" +
                "cbcbcbcbbdabcbbbcbbcbbbcbbbbcbabbbabab9a89013444443443443353343344234333433423423333333423221201" +
                "889bccccbdbccbbc777777771999aaabbbbbcaba9a9801235443534335233423223211188abdcbdcbbdbbbcbcabbaaaaa" +
                "8802253543443424233342322120189bbdcccbcbcbcbbcabbabba99901244443533533343423232221008abdbebcbc" +
                "bccabbcababab9a8801344534434335233342322211089acbdccbcbcbcbbbcbbabab9a8002444434434343342333323" +
                "12008abdcccbccbbdabbcabbabaa99802245353443343433334232121089abdccbdbcbbdabbcabaaba9990023543543" +
                "3533343423322222008aadbdcbccbcacabbbcabaa9a8901335444343434334233233211189accccbdbbdbbbcbcababaa" +
                "a988023535443344334",
        )
        val a2 = hexToBytes(
            "e32c31520938cbcbbcbcbbcbcabcbacabacaabbabbbbabaa998012363543533534343353335234333433423423333334" +
                "232222110089bbebdcbcbdbbdbbcbcbcbbcbbcbcabcabbbcabbbbbbcaaaa9a8881234444435335334433434334334342" +
                "334333334333333332222008aadcccbcccbcbcbcbcbbcbcbcacabbbcbbbbcbbbcabbabaaaaa89011435435344343434" +
                "423433433434242233423333334232321210089abebdbdbcbccbbdbbcbbdabcbbbcbbcbbbbcbbcabababbaaa9988113" +
                "54435344343434343433433433433433342334223232322111089accbdcbdbcbcbccbbcbbccabcbbbcbbcabcabbbbbbb" +
                "caaaaa9988022524222322120089bbebdbccbbccabbbcabaaa998012436344335333434232322110099cbdcbdbbdbbcac" +
                "ababaaaa99811353543533434333423322211089adbdcbcbdbbbccababbaba99881244444343434333432333221009ab" +
                "ddbccbdacabbcbabbbbaaa8802354443443343433334222211089abebdbcbdbbbcbcbabbaba999012363543434343334" +
                "33233221008abebdbccbcbcbbcabbbbbaa99801354443443343433334223120189accbdcbcbcbcbbbcbbabab99900244" +
                "443443434334233332312008abdcccbccbcacabbbcaaba999801244435343442334233232221009acccccbcbcbcbbbcb" +
                "abbbaa9881235",
        )
        assertEquals(BridgeProtocol.ADPCM_FRAME_BYTES, a1.size)
        assertEquals(BridgeProtocol.ADPCM_FRAME_BYTES, a2.size)

        val pcm1 = ByteArray(BridgeProtocol.FRAME_BYTES)
        assertTrue(ImaAdpcmDecoder.decodeFrame(a1, 0, pcm1))
        val expected1First8 = intArrayOf(0, 11, 11, 41, 41, 104, 104, 240)
        for (i in expected1First8.indices) {
            assertEquals("f1 sample $i", expected1First8[i], readLeShort(pcm1, i))
        }

        val pcm2 = ByteArray(BridgeProtocol.FRAME_BYTES)
        assertTrue(ImaAdpcmDecoder.decodeFrame(a2, 0, pcm2))
        val expected2First8 = intArrayOf(10596, 3356, 9755, 4943, 8770, 6009, 7843, 6979)
        for (i in expected2First8.indices) {
            assertEquals("f2 first sample $i", expected2First8[i], readLeShort(pcm2, i))
        }
        val expected2Last8 = intArrayOf(-17993, -11297, -17836, -10989, -17693, -10597, -17406, -10036)
        val base = (BridgeProtocol.FRAME_BYTES / 2) - 8
        for (i in expected2Last8.indices) {
            assertEquals("f2 last sample $i", expected2Last8[i], readLeShort(pcm2, base + i))
        }
    }

    @Test
    fun rejectsInvalidBounds() {
        val shortSrc = ByteArray(100)
        val dst = ByteArray(BridgeProtocol.FRAME_BYTES)
        assertFalse(ImaAdpcmDecoder.decodeFrame(shortSrc, 0, dst))
        assertFalse(ImaAdpcmDecoder.decodeFrame(ByteArray(486), 1, dst))
    }
}
