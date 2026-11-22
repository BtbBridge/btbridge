package com.btbridge.app.service

import android.content.Context
import com.btbridge.app.audio.JitterProfile
import com.btbridge.app.protocol.BridgeProtocol
import com.btbridge.app.ui.AppLanguage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.util.Locale

enum class ConnectionMode {
    USB,
    WIFI,
}

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    RECONNECTING,
}

data class BridgeUiState(
    val status: ConnectionStatus = ConnectionStatus.DISCONNECTED,
    val mode: ConnectionMode = ConnectionMode.USB,
    val wifiIp: String = "192.168.1.100",
    val port: Int = BridgeProtocol.DEFAULT_PORT,
    val jitterProfile: JitterProfile = JitterProfile.BALANCED,
    val latencyMs: Long? = null,
    val bitrateKbps: Int = 0,
    val bufferFillMs: Int = 0,
    val statusMessage: String = "Hazır • USB kablosunu bağlayıp dokunun",
    val language: AppLanguage = AppLanguage.TR,
    val needsLanguageChoice: Boolean = false,
)

object BridgeStateRepository {
    private const val PREFS_NAME = "btbridge_prefs"
    private const val KEY_WIFI_IP = "wifi_ip"
    private const val KEY_PORT = "port"
    private const val KEY_PROFILE = "jitter_profile"
    private const val KEY_LANGUAGE = "app_language"

    private val _state = MutableStateFlow(BridgeUiState())
    val state: StateFlow<BridgeUiState> = _state.asStateFlow()

    @Volatile
    private var prefsLoaded = false

    fun loadPreferences(context: Context) {
        if (prefsLoaded) return
        prefsLoaded = true
        val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val savedIp = prefs.getString(KEY_WIFI_IP, "192.168.1.100") ?: "192.168.1.100"
        val savedPort = prefs.getInt(KEY_PORT, BridgeProtocol.DEFAULT_PORT)
        val savedProfile = JitterProfile.fromId(prefs.getString(KEY_PROFILE, null))
        val savedLang = AppLanguage.fromCode(prefs.getString(KEY_LANGUAGE, null))
        val defaultLang = if (Locale.getDefault().language.equals("tr", ignoreCase = true)) {
            AppLanguage.TR
        } else {
            AppLanguage.EN
        }
        _state.update {
            it.copy(
                wifiIp = savedIp,
                port = savedPort,
                jitterProfile = savedProfile,
                language = savedLang ?: defaultLang,
                needsLanguageChoice = (savedLang == null),
            )
        }
    }

    fun updateLanguage(context: Context, language: AppLanguage) {
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_LANGUAGE, language.code)
            .apply()
        _state.update {
            it.copy(
                language = language,
                needsLanguageChoice = false,
            )
        }
    }

    fun updateWifiConfig(context: Context, ip: String, port: Int) {
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_WIFI_IP, ip)
            .putInt(KEY_PORT, port)
            .apply()
        _state.update { it.copy(wifiIp = ip, port = port) }
    }

    fun updateJitterProfile(context: Context, profile: JitterProfile) {
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PROFILE, profile.id)
            .apply()
        _state.update { it.copy(jitterProfile = profile) }
    }

    fun updateStatus(
        status: ConnectionStatus,
        mode: ConnectionMode = _state.value.mode,
        statusMessage: String? = null,
    ) {
        _state.update { current ->
            current.copy(
                status = status,
                mode = mode,
                statusMessage = statusMessage ?: current.statusMessage,
                latencyMs = if (status == ConnectionStatus.DISCONNECTED) null else current.latencyMs,
                bitrateKbps = if (status != ConnectionStatus.CONNECTED) 0 else current.bitrateKbps,
                bufferFillMs = if (status != ConnectionStatus.CONNECTED) 0 else current.bufferFillMs,
            )
        }
    }

    fun updateTelemetry(
        latencyMs: Long? = _state.value.latencyMs,
        bitrateKbps: Int = _state.value.bitrateKbps,
        bufferFillMs: Int = _state.value.bufferFillMs,
    ) {
        _state.update {
            it.copy(
                latencyMs = latencyMs,
                bitrateKbps = bitrateKbps,
                bufferFillMs = bufferFillMs,
            )
        }
    }
}
