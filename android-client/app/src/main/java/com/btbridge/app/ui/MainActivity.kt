package com.btbridge.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.btbridge.app.audio.BluetoothDeviceMonitor
import com.btbridge.app.audio.JitterProfile
import com.btbridge.app.service.AudioBridgeService
import com.btbridge.app.service.BridgeStateRepository
import com.btbridge.app.service.ConnectionMode
import com.btbridge.app.ui.theme.BTBridgeTheme

class MainActivity : ComponentActivity() {

    private lateinit var bluetoothMonitor: BluetoothDeviceMonitor

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        BridgeStateRepository.loadPreferences(this)
        bluetoothMonitor = BluetoothDeviceMonitor(this)
        requestNotificationPermissionIfNeeded()

        setContent {
            BTBridgeTheme {
                val uiState by BridgeStateRepository.state.collectAsStateWithLifecycle()
                val btInfo by bluetoothMonitor.bluetoothInfo.collectAsStateWithLifecycle()

                BTBridgeScreen(
                    uiState = uiState,
                    btInfo = btInfo,
                    onConnectUsb = {
                        AudioBridgeService.startBridge(
                            context = this,
                            mode = ConnectionMode.USB,
                            host = "127.0.0.1",
                            port = uiState.port,
                            profile = uiState.jitterProfile,
                        )
                    },
                    onConnectWifi = { ip, port ->
                        if (ip.isNotBlank()) {
                            BridgeStateRepository.updateWifiConfig(this, ip, port)
                            AudioBridgeService.startBridge(
                                context = this,
                                mode = ConnectionMode.WIFI,
                                host = ip,
                                port = port,
                                profile = uiState.jitterProfile,
                            )
                        }
                    },
                    onDisconnect = {
                        AudioBridgeService.stopBridge(this)
                    },
                    onSelectJitterProfile = { profile: JitterProfile ->
                        BridgeStateRepository.updateJitterProfile(this, profile)
                        if (uiState.status != com.btbridge.app.service.ConnectionStatus.DISCONNECTED) {
                            AudioBridgeService.setProfile(this, profile)
                        }
                    },
                    onSelectLanguage = { lang ->
                        BridgeStateRepository.updateLanguage(this, lang)
                    },
                )
            }
        }
    }

    override fun onStart() {
        super.onStart()
        bluetoothMonitor.start()
    }

    override fun onStop() {
        bluetoothMonitor.stop()
        super.onStop()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
}
