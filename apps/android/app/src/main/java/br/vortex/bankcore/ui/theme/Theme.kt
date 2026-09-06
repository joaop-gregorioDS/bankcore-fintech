package br.vortex.bankcore.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

fun hex(value: String): Color {
    val raw = value.removePrefix("#")
    val parsed = raw.toLong(16)
    return Color(
        red = ((parsed shr 16) and 0xFF) / 255f,
        green = ((parsed shr 8) and 0xFF) / 255f,
        blue = (parsed and 0xFF) / 255f,
    )
}

@Immutable
data class BankPalette(
    val ink: Color,
    val panel: Color,
    val card: Color,
    val ivory: Color,
    val mute: Color,
    val gold: Color,
    val goldDim: Color,
    val debit: Color,
    val status: Color,
    val line: Color,
    val input: Color,
    val onGold: Color,
    val isDark: Boolean,
) {
    val material: ColorScheme
        get() = if (isDark) {
            darkColorScheme(
                primary = gold,
                onPrimary = onGold,
                background = ink,
                onBackground = ivory,
                surface = card,
                onSurface = ivory,
                surfaceVariant = panel,
                outline = line,
                error = debit,
            )
        } else {
            lightColorScheme(
                primary = gold,
                onPrimary = onGold,
                background = ink,
                onBackground = ivory,
                surface = card,
                onSurface = ivory,
                surfaceVariant = panel,
                outline = line,
                error = debit,
            )
        }
}

val LightPalette = BankPalette(
    ink = hex("#F4F1EA"),
    panel = hex("#FFFFFF"),
    card = hex("#FFFFFF"),
    ivory = hex("#121212"),
    mute = hex("#6B6560"),
    gold = hex("#9A7B32"),
    goldDim = hex("#7A6228"),
    debit = hex("#B42318"),
    status = hex("#2F6B4F"),
    line = hex("#E4DFD4"),
    input = hex("#FAF8F3"),
    onGold = hex("#0B0B0C"),
    isDark = false,
)

val DarkPalette = BankPalette(
    ink = hex("#0B0B0C"),
    panel = hex("#141416"),
    card = hex("#1C1C1F"),
    ivory = hex("#F6F1E8"),
    mute = hex("#9A958C"),
    gold = hex("#C4A35A"),
    goldDim = hex("#8A7340"),
    debit = hex("#C42B2B"),
    status = hex("#3D7A5A"),
    line = hex("#2A2A2E"),
    input = hex("#141416"),
    onGold = hex("#0B0B0C"),
    isDark = true,
)

object Paper {
    val bg = hex("#F4F1EA")
    val ink = hex("#121212")
    val mute = hex("#6B6560")
    val gold = hex("#9A7B32")
    val line = hex("#E4DFD4")
    val debit = hex("#B42318")
}

private val LocalPalette = staticCompositionLocalOf { LightPalette }

val Palette: BankPalette
    @Composable get() = LocalPalette.current

val BankTypography = Typography(
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
    ),
    labelMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 12.sp,
    ),
)

@Composable
fun BankCoreTheme(darkTheme: Boolean, content: @Composable () -> Unit) {
    val palette = if (darkTheme) DarkPalette else LightPalette
    CompositionLocalProvider(LocalPalette provides palette) {
        MaterialTheme(
            colorScheme = palette.material,
            typography = BankTypography,
            content = content,
        )
    }
}
