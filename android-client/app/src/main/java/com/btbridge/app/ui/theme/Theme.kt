package com.btbridge.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val BgDark = Color(0xFF0B1120)
val SurfaceDark = Color(0xFF162032)
val SurfaceVariantDark = Color(0xFF1E293B)
val BorderDark = Color(0xFF2A3950)
val EmeraldPrimary = Color(0xFF10B981)
val SkyAccent = Color(0xFF38BDF8)
val AmberWarn = Color(0xFFF59E0B)
val RoseError = Color(0xFFF43F5E)
val TextPrimary = Color(0xFFF8FAFC)
val TextMuted = Color(0xFF94A3B8)

private val BTBridgeColorScheme = darkColorScheme(
    primary = EmeraldPrimary,
    onPrimary = Color(0xFF022C22),
    secondary = SkyAccent,
    onSecondary = Color(0xFF082F49),
    background = BgDark,
    onBackground = TextPrimary,
    surface = SurfaceDark,
    onSurface = TextPrimary,
    surfaceVariant = SurfaceVariantDark,
    onSurfaceVariant = TextMuted,
    error = RoseError,
    outline = BorderDark,
)

@Composable
fun BTBridgeTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = BTBridgeColorScheme,
        content = content,
    )
}
