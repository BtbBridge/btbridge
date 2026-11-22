package com.btbridge.app.audio

import android.content.Context
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class BluetoothOutputInfo(
    val isConnected: Boolean = false,
    val deviceName: String = "Bağlı Bluetooth Cihaz Yok",
    val typeLabel: String = "Telefon Hoparlörü / Kablolu",
)

class BluetoothDeviceMonitor(context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val handler = Handler(Looper.getMainLooper())

    private val _bluetoothInfo = MutableStateFlow(BluetoothOutputInfo())
    val bluetoothInfo: StateFlow<BluetoothOutputInfo> = _bluetoothInfo.asStateFlow()

    private val callback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
            refresh()
        }

        override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>) {
            refresh()
        }
    }

    fun start() {
        refresh()
        audioManager.registerAudioDeviceCallback(callback, handler)
    }

    fun stop() {
        audioManager.unregisterAudioDeviceCallback(callback)
    }

    fun refresh() {
        _bluetoothInfo.value = queryBluetoothOutput()
    }

    private fun queryBluetoothOutput(): BluetoothOutputInfo {
        return try {
            val outputs = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            val preferred = outputs.firstOrNull { isPreferredBluetoothType(it.type) }
                ?: outputs.firstOrNull { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }

            if (preferred == null) {
                BluetoothOutputInfo()
            } else {
                val rawName = preferred.productName?.toString()?.trim().orEmpty()
                val name = rawName.ifEmpty { "Bluetooth Ses Cihazı" }
                BluetoothOutputInfo(
                    isConnected = true,
                    deviceName = name,
                    typeLabel = typeLabel(preferred.type),
                )
            }
        } catch (_: SecurityException) {
            BluetoothOutputInfo(
                isConnected = false,
                deviceName = "Bluetooth İzin Bekliyor",
                typeLabel = "Sistem Çıkışı",
            )
        }
    }

    private fun isPreferredBluetoothType(type: Int): Boolean {
        if (type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP) return true
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (type == AudioDeviceInfo.TYPE_BLE_HEADSET || type == AudioDeviceInfo.TYPE_BLE_SPEAKER) {
                return true
            }
        }
        return false
    }

    private fun typeLabel(type: Int): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (type == AudioDeviceInfo.TYPE_BLE_HEADSET) return "LE Audio Kulaklık"
            if (type == AudioDeviceInfo.TYPE_BLE_SPEAKER) return "LE Audio Hoparlör"
        }
        return when (type) {
            AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "Bluetooth A2DP"
            AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "Bluetooth SCO"
            else -> "Bluetooth"
        }
    }
}
