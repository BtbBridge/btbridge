package com.btbridge.app.ui

import com.btbridge.app.audio.JitterProfile

enum class AppLanguage(val code: String) {
    TR("tr"),
    EN("en"),
    ;

    companion object {
        fun fromCode(code: String?): AppLanguage? =
            entries.firstOrNull { it.code.equals(code?.trim(), ignoreCase = true) }
    }
}

data class AppStrings(
    val subtitle: String,
    val statusConnected: String,
    val statusConnecting: String,
    val statusReconnecting: String,
    val statusReady: String,
    val audioOutputTitle: String,
    val noBluetoothTitle: String,
    val noBluetoothSubtitle: String,
    val latencyLabel: String,
    val bitrateLabel: String,
    val bufferLabel: String,
    val usbModeTitle: String,
    val readyHint: String,
    val connectUsb: String,
    val disconnect: String,
    val jitterSectionTitle: String,
    val wifiModeTitle: String,
    val pcIpLabel: String,
    val portLabel: String,
    val connectWifi: String,
    val disconnectWifi: String,
    val langDialogTitle: String,
    val langDialogBody: String,
    val langTurkish: String,
    val langEnglish: String,
    val jitterLabels: Map<JitterProfile, String>,
    val jitterDescriptions: Map<JitterProfile, String>,
)

private val TR_STRINGS = AppStrings(
    subtitle = "PC -> Bluetooth Ses Köprüsü",
    statusConnected = "Bağlı",
    statusConnecting = "Bağlanıyor",
    statusReconnecting = "Yeniden Bağlanıyor",
    statusReady = "Hazır",
    audioOutputTitle = "Ses Çıkış Cihazı",
    noBluetoothTitle = "Bağlı Bluetooth Cihaz Yok",
    noBluetoothSubtitle = "Telefon Hoparlörü / Kablolu",
    latencyLabel = "Gecikme (RTT)",
    bitrateLabel = "Veri Hızı",
    bufferLabel = "Tampon",
    usbModeTitle = "Birincil Mod: USB Kablo (ADB Reverse)",
    readyHint = "Hazır • USB kablosunu bağlayıp dokunun",
    connectUsb = "USB ile Bağlan",
    disconnect = "Bağlantıyı Kes",
    jitterSectionTitle = "Jitter Tampon Profili",
    wifiModeTitle = "İkincil Mod: Yerel Wi-Fi",
    pcIpLabel = "PC IP Adresi",
    portLabel = "Port",
    connectWifi = "Wi-Fi ile Bağlan",
    disconnectWifi = "Wi-Fi Bağlantısını Kes",
    langDialogTitle = "Dil Seçin / Choose Language",
    langDialogBody = "Uygulama dilini seçin • Select app language",
    langTurkish = "Türkçe",
    langEnglish = "English",
    jitterLabels = mapOf(
        JitterProfile.ULTRA_LOW to "Ultra Düşük (~20ms)",
        JitterProfile.BALANCED to "Dengeli (~40ms)",
        JitterProfile.STABLE to "Kararlı (~80ms)",
        JitterProfile.WIFI_SAFE to "Wi-Fi Ekstra Kararlı (~140ms)",
    ),
    jitterDescriptions = mapOf(
        JitterProfile.ULTRA_LOW to "Kablolu USB için en düşük gecikme",
        JitterProfile.BALANCED to "Günlük kullanım ve video için ideal",
        JitterProfile.STABLE to "Wi-Fi veya yoğun ağda sıfır cızırtı",
        JitterProfile.WIFI_SAFE to "Zayıf / 2.4 GHz Wi-Fi ve BT kulaklık için sıfır kopma",
    ),
)

private val EN_STRINGS = AppStrings(
    subtitle = "PC -> Bluetooth Audio Bridge",
    statusConnected = "Connected",
    statusConnecting = "Connecting",
    statusReconnecting = "Reconnecting",
    statusReady = "Ready",
    audioOutputTitle = "Audio Output Device",
    noBluetoothTitle = "No Bluetooth Device Connected",
    noBluetoothSubtitle = "Phone Speaker / Wired",
    latencyLabel = "Latency (RTT)",
    bitrateLabel = "Bitrate",
    bufferLabel = "Buffer",
    usbModeTitle = "Primary Mode: USB Cable (ADB Reverse)",
    readyHint = "Ready • Connect USB cable and tap",
    connectUsb = "Connect via USB",
    disconnect = "Disconnect",
    jitterSectionTitle = "Jitter Buffer Profile",
    wifiModeTitle = "Secondary Mode: Local Wi-Fi",
    pcIpLabel = "PC IP Address",
    portLabel = "Port",
    connectWifi = "Connect via Wi-Fi",
    disconnectWifi = "Disconnect Wi-Fi",
    langDialogTitle = "Dil Seçin / Choose Language",
    langDialogBody = "Uygulama dilini seçin • Select app language",
    langTurkish = "Türkçe",
    langEnglish = "English",
    jitterLabels = mapOf(
        JitterProfile.ULTRA_LOW to "Ultra Low (~20ms)",
        JitterProfile.BALANCED to "Balanced (~40ms)",
        JitterProfile.STABLE to "Stable (~80ms)",
        JitterProfile.WIFI_SAFE to "Wi-Fi Extra Stable (~140ms)",
    ),
    jitterDescriptions = mapOf(
        JitterProfile.ULTRA_LOW to "Lowest latency over wired USB",
        JitterProfile.BALANCED to "Ideal for daily use and video",
        JitterProfile.STABLE to "Zero crackle on Wi-Fi or busy networks",
        JitterProfile.WIFI_SAFE to "Zero dropouts on weak 2.4 GHz Wi-Fi & BT",
    ),
)

fun stringsFor(lang: AppLanguage): AppStrings =
    when (lang) {
        AppLanguage.TR -> TR_STRINGS
        AppLanguage.EN -> EN_STRINGS
    }
