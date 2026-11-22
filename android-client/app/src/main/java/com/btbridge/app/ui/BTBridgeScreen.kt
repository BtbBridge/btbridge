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
import androidx.compose.material3.AlertDialog
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
import androidx.compose.material3.TextButton
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
    onSelectLanguage: (AppLanguage) -> Unit = {},
) {
    val s = stringsFor(uiState.language)
    var wifiIpInput by rememberSaveable(uiState.wifiIp) { mutableStateOf(uiState.wifiIp) }
    var wifiPortInput by rememberSaveable(uiState.port) { mutableStateOf(uiState.port.toString()) }

    val isActive = uiState.status != ConnectionStatus.DISCONNECTED
    val statusColor = when (uiState.status) {
        ConnectionStatus.CONNECTED -> EmeraldPrimary
        ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING -> AmberWarn
        ConnectionStatus.DISCONNECTED -> TextMuted
    }
    val statusText = when (uiState.status) {
        ConnectionStatus.CONNECTED -> s.statusConnected
        ConnectionStatus.CONNECTING -> s.statusConnecting
        ConnectionStatus.RECONNECTING -> s.statusReconnecting
        ConnectionStatus.DISCONNECTED -> s.statusReady
    }

    if (uiState.needsLanguageChoice) {
        AlertDialog(
            onDismissRequest = { onSelectLanguage(uiState.language) },
            containerColor = SurfaceDark,
            titleContentColor = TextPrimary,
            textContentColor = TextMuted,
            title = {
                Text(
                    text = s.langDialogTitle,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                )
            },
            text = {
                Text(
                    text = s.langDialogBody,
                    fontSize = 14.sp,
                )
            },
            confirmButton = {
                Button(
                    onClick = { onSelectLanguage(AppLanguage.TR) },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = EmeraldPrimary,
                        contentColor = Color(0xFF022C22),
                    ),
                ) {
                    Text(s.langTurkish, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(
                    onClick = { onSelectLanguage(AppLanguage.EN) },
                    border = BorderStroke(1.dp, SkyAccent),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = SkyAccent),
                ) {
                    Text(s.langEnglish, fontWeight = FontWeight.SemiBold)
                }
            },
        )
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
            // Başlık, Dil Seçici ve Durum Rozeti
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "BTBridge",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                    )
                    Text(
                        text = s.subtitle,
                        fontSize = 13.sp,
                        color = TextMuted,
                    )
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = SurfaceVariantDark,
                        border = BorderStroke(1.dp, BorderDark),
                        modifier = Modifier
                            .clip(RoundedCornerShape(16.dp))
                            .clickable {
                                val next = if (uiState.language == AppLanguage.TR) AppLanguage.EN else AppLanguage.TR
                                onSelectLanguage(next)
                            },
                    ) {
                        Text(
                            text = if (uiState.language == AppLanguage.TR) "TR | EN" else "EN | TR",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            color = SkyAccent,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
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
                            text = s.audioOutputTitle,
                            fontSize = 11.sp,
                            color = TextMuted,
                        )
                        Text(
                            text = if (btInfo.isConnected) btInfo.deviceName else s.noBluetoothTitle,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                        Text(
                            text = if (btInfo.isConnected) btInfo.typeLabel else s.noBluetoothSubtitle,
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
                    label = s.latencyLabel,
                    value = uiState.latencyMs?.let { "$it ms" } ?: "-- ms",
                    accent = SkyAccent,
                )
                TelemetryCard(
                    modifier = Modifier.weight(1f),
                    label = s.bitrateLabel,
                    value = "${uiState.bitrateKbps} kbps",
                    accent = EmeraldPrimary,
                )
                TelemetryCard(
                    modifier = Modifier.weight(1f),
                    label = s.bufferLabel,
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
                            text = s.usbModeTitle,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary,
                        )
                    }
                    Text(
                        text = if (uiState.status == ConnectionStatus.DISCONNECTED && uiState.statusMessage.startsWith("Hazır")) {
                            s.readyHint
                        } else {
                            uiState.statusMessage
                        },
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
                            Text(s.disconnect, fontWeight = FontWeight.Bold, fontSize = 15.sp)
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
                            Text(s.connectUsb, fontWeight = FontWeight.Bold, fontSize = 15.sp)
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
                            text = s.jitterSectionTitle,
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
                                        text = s.jitterLabels[profile] ?: profile.label,
                                        color = if (selected) EmeraldPrimary else TextPrimary,
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 14.sp,
                                    )
                                    Text(
                                        text = s.jitterDescriptions[profile] ?: "",
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
                            text = s.wifiModeTitle,
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
                            label = { Text(s.pcIpLabel) },
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
                            label = { Text(s.portLabel) },
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
                            Text(s.disconnectWifi, fontWeight = FontWeight.SemiBold)
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
                            Text(s.connectWifi, fontWeight = FontWeight.SemiBold)
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
