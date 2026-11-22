package com.btbridge.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.BluetoothConnected
import androidx.compose.material.icons.rounded.BluetoothDisabled
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.Speed
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.Usb
import androidx.compose.material.icons.rounded.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.btbridge.app.audio.BluetoothOutputInfo
import com.btbridge.app.audio.JitterProfile
import com.btbridge.app.protocol.BridgeProtocol
import com.btbridge.app.service.BridgeUiState
import com.btbridge.app.service.ConnectionMode
import com.btbridge.app.service.ConnectionStatus
import com.btbridge.app.ui.theme.AmberWarn
import com.btbridge.app.ui.theme.BgDark
import com.btbridge.app.ui.theme.BorderDark
import com.btbridge.app.ui.theme.EmeraldPrimary
import com.btbridge.app.ui.theme.RoseError
import com.btbridge.app.ui.theme.SkyAccent
import com.btbridge.app.ui.theme.SurfaceDark
import com.btbridge.app.ui.theme.SurfaceVariantDark
import com.btbridge.app.ui.theme.TextMuted
import com.btbridge.app.ui.theme.TextPrimary

@Composable
fun BTBridgeScreen(
    uiState: BridgeUiState,
    btInfo: BluetoothOutputInfo,
    onConnectUsb: () -> Unit,
    onConnectWifi: (ip: String, port: Int) -> Unit,
    onDisconnect: () -> Unit,
    onSelectJitterProfile: (JitterProfile) -> Unit,
) {
    var wifiIpInput by rememberSaveable(uiState.wifiIp) { mutableStateOf(uiState.wifiIp) }
    var wifiPortInput by rememberSaveable(uiState.port) { mutableStateOf(uiState.port.toString()) }

    val isActive = uiState.status != ConnectionStatus.DISCONNECTED
    val statusColor = when (uiState.status) {
        ConnectionStatus.CONNECTED -> EmeraldPrimary
        ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> AmberWarn
        ConnectionStatus.DISCONNECTED -> TextMuted
    }
    val statusText = when (uiState.status) {
        ConnectionStatus.CONNECTED -> "Bağlı"
        ConnectionStatus.CONNECTING -> "Bağlanıyor"
        ConnectionStatus.RECONNECTING -> "Yeniden Bağlanıyor"
        ConnectionStatus.DISCONNECTED -> "Hazır"
    }

    Scaffold(
        containerColor = BgDark,
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            // Başlık ve Durum Rozeti
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        text = "BTBridge",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                    )
                    Text(
                        text = "PC -> Bluetooth Ses Köprüsü",
                        fontSize = 13.sp,
                        color = TextMuted,
                    )
                }

                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = SurfaceVariantDark,
                    border = BorderStroke(1.dp, statusColor.copy(alpha = 0.5f)),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(statusColor),
                        )
                        Text(
                            text = statusText,
                            color = statusColor,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }

            // Bağlı Bluetooth Cihaz Kartı
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(
                    1.dp,
                    if (btInfo.isConnected) SkyAccent.copy(alpha = 0.45f) else BorderDark,
                ),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                if (btInfo.isConnected) SkyAccent.copy(alpha = 0.16f) else SurfaceVariantDark,
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            imageVector = if (btInfo.isConnected) {
                                Icons.Rounded.BluetoothConnected
                            } else {
                                Icons.Rounded.BluetoothDisabled
                            },
                            contentDescription = null,
                            tint = if (btInfo.isConnected) SkyAccent else TextMuted,
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Ses Çıkış Cihazı",
                            fontSize = 11.sp,
                            color = TextMuted,
                        )
                        Text(
                            text = btInfo.deviceName,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                        Text(
                            text = btInfo.typeLabel,
                            fontSize = 12.sp,
                            color = if (btInfo.isConnected) SkyAccent else TextMuted,
                        )
                    }
                }
            }

            // Canlı Telemetri Kartları
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                TelemetryCard(
                    modifier = Modifier.weight(1f),
                    label = "Gecikme (RTT)",
                    value = uiState.latencyMs?.let { "$it ms" } ?: "-- ms",
                    accent = SkyAccent,
                )
                TelemetryCard(
                    modifier = Modifier.weight(1f),
                    label = "Veri Hızı",
                    value = "${uiState.bitrateKbps} kbps",
                    accent = EmeraldPrimary,
                )
                TelemetryCard(
                    modifier = Modifier.weight(1f),
                    label = "Tampon",
                    value = "${uiState.bufferFillMs} ms",
                    accent = AmberWarn,
                )
            }

            // USB ile Bağlan / Durdur Kartı
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, BorderDark),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.Usb, contentDescription = null, tint = EmeraldPrimary)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Birincil Mod: USB Kablo (ADB Reverse)",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                    }
                    Text(
                        text = uiState.statusMessage,
                        fontSize = 12.sp,
                        color = TextMuted,
                    )

                    if (isActive && uiState.mode == ConnectionMode.USB) {
                        Button(
                            onClick = onDisconnect,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = RoseError,
                                contentColor = Color.White,
                            ),
                        ) {
                            Icon(Icons.Rounded.PowerSettingsNew, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Bağlantıyı Kes", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        }
                    } else {
                        Button(
                            onClick = onConnectUsb,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = EmeraldPrimary,
                                contentColor = Color(0xFF022C22),
                            ),
                        ) {
                            Icon(Icons.Rounded.Usb, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("USB ile Bağlan", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        }
                    }
                }
            }

            // Jitter Buffer Profili Seçici
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, BorderDark),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.Tune, contentDescription = null, tint = SkyAccent)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Jitter Tampon Profili",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                    }

                    JitterProfile.entries.forEach { profile ->
                        val selected = uiState.jitterProfile == profile
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .clickable { onSelectJitterProfile(profile) },
                            color = if (selected) EmeraldPrimary.copy(alpha = 0.14f) else SurfaceVariantDark,
                            border = BorderStroke(
                                1.dp,
                                if (selected) EmeraldPrimary else BorderDark,
                            ),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Column {
                                    Text(
                                        text = profile.label,
                                        color = if (selected) EmeraldPrimary else TextPrimary,
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 14.sp,
                                    )
                                    Text(
                                        text = when (profile) {
                                            JitterProfile.ULTRA_LOW -> "Kablolu USB için en düşük gecikme"
                                            JitterProfile.BALANCED -> "Günlük kullanım ve video için ideal"
                                            JitterProfile.STABLE -> "Wi-Fi veya yoğun ağda sıfır cızırtı"
                                            JitterProfile.WIFI_SAFE -> "Zayıf / 2.4 GHz Wi-Fi ve BT kulaklık için sıfır kopma"
                                        },
                                        color = TextMuted,
                                        fontSize = 11.sp,
                                    )
                                }
                                if (selected) {
                                    Icon(
                                        imageVector = Icons.Rounded.CheckCircle,
                                        contentDescription = null,
                                        tint = EmeraldPrimary,
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // İkincil Mod: Yerel Wi-Fi Bağlantısı
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceDark),
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, BorderDark),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.Wifi, contentDescription = null, tint = SkyAccent)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "İkincil Mod: Yerel Wi-Fi",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        OutlinedTextField(
                            value = wifiIpInput,
                            onValueChange = { wifiIpInput = it },
                            label = { Text("PC IP Adresi") },
                            singleLine = true,
                            modifier = Modifier.weight(2f),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = SkyAccent,
                                unfocusedBorderColor = BorderDark,
                                focusedTextColor = TextPrimary,
                                unfocusedTextColor = TextPrimary,
                            ),
                        )
                        OutlinedTextField(
                            value = wifiPortInput,
                            onValueChange = { wifiPortInput = it.filter(Char::isDigit) },
                            label = { Text("Port") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = SkyAccent,
                                unfocusedBorderColor = BorderDark,
                                focusedTextColor = TextPrimary,
                                unfocusedTextColor = TextPrimary,
                            ),
                        )
                    }

                    if (isActive && uiState.mode == ConnectionMode.WIFI) {
                        OutlinedButton(
                            onClick = onDisconnect,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, RoseError),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = RoseError),
                        ) {
                            Text("Wi-Fi Bağlantısını Kes", fontWeight = FontWeight.SemiBold)
                        }
                    } else {
                        OutlinedButton(
                            onClick = {
                                val parsedPort = wifiPortInput.toIntOrNull()
                                    ?.takeIf { it in 1..65535 }
                                    ?: BridgeProtocol.DEFAULT_PORT
                                onConnectWifi(wifiIpInput.trim(), parsedPort)
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, SkyAccent),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = SkyAccent),
                        ) {
                            Icon(Icons.Rounded.Speed, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Wi-Fi ile Bağlan", fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TelemetryCard(
    modifier: Modifier = Modifier,
    label: String,
    value: String,
    accent: Color,
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, BorderDark),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 12.dp),
        ) {
            Text(
                text = label,
                fontSize = 11.sp,
                color = TextMuted,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = accent,
            )
        }
    }
}
