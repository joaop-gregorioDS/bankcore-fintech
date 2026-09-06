package br.vortex.bankcore.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.outlined.NorthEast
import androidx.compose.material.icons.outlined.SouthWest
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.data.LedgerTransaction
import br.vortex.bankcore.data.MockCard
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.ui.theme.hex
import br.vortex.bankcore.util.BankDate
import br.vortex.bankcore.util.Money

@Composable
fun Wordmark(size: Int = 32, modifier: Modifier = Modifier) {
    val p = Palette
    Row(modifier = modifier) {
        Text(
            "Bank",
            color = p.ivory,
            fontSize = size.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = (-0.4).sp,
        )
        Text(
            "Core",
            color = p.gold,
            fontSize = size.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = (-0.4).sp,
        )
    }
}

@Composable
fun BrandMark(size: Dp = 48.dp, modifier: Modifier = Modifier) {
    val gold = Palette.gold
    Canvas(modifier = modifier.size(size)) {
        val stroke = maxOf(1.2.dp.toPx(), size.toPx() * 0.035f)
        val inset = stroke / 2
        val radius = size.toPx() * 0.22f
        drawRoundRect(
            color = gold,
            topLeft = Offset(inset, inset),
            size = Size(this.size.width - stroke, this.size.height - stroke),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(radius, radius),
            style = Stroke(width = stroke),
        )
        val cx = this.size.width / 2
        val cy = this.size.height / 2 + this.size.height * 0.02f
        val w = this.size.width * 0.38f
        val h = this.size.height * 0.42f
        val path = Path().apply {
            val left = cx - w / 2
            val right = cx + w / 2
            val top = cy - h * 0.46f
            val bottom = cy + h * 0.50f
            val r = w * 0.22f
            val waist = cy + h * 0.08f
            moveTo(left + r, top)
            quadraticTo(left, top, left, top + r)
            lineTo(left, waist)
            quadraticTo(left + w * 0.06f, bottom - h * 0.12f, cx, bottom)
            quadraticTo(right - w * 0.06f, bottom - h * 0.12f, right, waist)
            lineTo(right, top + r)
            quadraticTo(right, top, right - r, top)
            close()
        }
        drawPath(
            path,
            color = gold,
            style = Stroke(width = stroke, cap = StrokeCap.Round, join = StrokeJoin.Round),
        )
    }
}

@Composable
fun VersionLabel(modifier: Modifier = Modifier) {
    Text(
        "version 1.10.25",
        modifier = modifier,
        fontSize = 11.sp,
        fontWeight = FontWeight.Medium,
        fontFamily = FontFamily.Monospace,
        color = Palette.mute,
        letterSpacing = 0.6.sp,
    )
}

@Composable
fun CarbonCard(
    modifier: Modifier = Modifier,
    padding: Dp = 16.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val p = Palette
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(p.card)
            .border(1.dp, p.line, RoundedCornerShape(12.dp))
            .padding(padding),
        content = content,
    )
}

@Composable
fun GoldButton(
    title: String,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    isLoading: Boolean = false,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    val p = Palette
    val active = enabled && !isLoading
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(if (active) p.gold else p.gold.copy(alpha = 0.35f))
            .clickable(enabled = active, onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(16.dp),
                color = p.onGold,
                strokeWidth = 2.dp,
            )
            Spacer(Modifier.width(8.dp))
        } else if (icon != null) {
            Icon(icon, contentDescription = null, tint = p.onGold, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
        }
        Text(
            title.uppercase(),
            color = p.onGold,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = 0.8.sp,
        )
    }
}

@Composable
fun SecondaryButton(
    title: String,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    onClick: () -> Unit,
) {
    val p = Palette
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .border(1.dp, p.line, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 13.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = p.ivory, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
        }
        Text(title, color = p.ivory, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun CarbonField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "",
    keyboardType: KeyboardType = KeyboardType.Text,
    isSecure: Boolean = false,
    mono: Boolean = false,
) {
    val p = Palette
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = p.mute)
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text(placeholder, color = p.mute) },
            singleLine = true,
            visualTransformation = if (isSecure) PasswordVisualTransformation() else VisualTransformation.None,
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
            textStyle = androidx.compose.ui.text.TextStyle(
                fontSize = 15.sp,
                color = p.ivory,
                fontFamily = if (mono) FontFamily.Monospace else FontFamily.SansSerif,
            ),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = p.gold,
                unfocusedBorderColor = p.line,
                focusedContainerColor = p.input,
                unfocusedContainerColor = p.input,
                cursorColor = p.gold,
                focusedTextColor = p.ivory,
                unfocusedTextColor = p.ivory,
            ),
            shape = RoundedCornerShape(8.dp),
        )
    }
}

@Composable
fun DemoBanner() {
    Text(
        "Ambiente de portfólio — login, Pix, extrato e comprovante no ledger interno",
        fontSize = 11.sp,
        fontWeight = FontWeight.Medium,
        color = Palette.gold,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
fun AmountText(value: Double, credit: Boolean? = null, size: Int = 15) {
    val p = Palette
    val label = if (credit != null) Money.signed(value, credit) else Money.reais(value)
    val color = if (credit == false) p.debit else p.ivory
    Text(
        label,
        fontSize = size.sp,
        fontWeight = FontWeight.SemiBold,
        fontFamily = FontFamily.Monospace,
        color = color,
    )
}

@Composable
fun TransactionRow(transaction: LedgerTransaction, onClick: () -> Unit) {
    val p = Palette
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val tint = if (transaction.isCredit) p.gold else p.debit
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(tint.copy(alpha = 0.12f))
                .border(1.dp, tint.copy(alpha = 0.28f), RoundedCornerShape(8.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                if (transaction.isCredit) Icons.Outlined.SouthWest else Icons.Outlined.NorthEast,
                contentDescription = null,
                tint = tint,
                modifier = Modifier.size(14.dp),
            )
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                transaction.title,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = p.ivory,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                "${BankDate.short(transaction.createdAt)} · ${transaction.idempotencyKey.take(12)}…",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = p.mute,
            )
        }
        Spacer(Modifier.width(8.dp))
        AmountText(transaction.amountReais, credit = transaction.isCredit)
    }
}

@Composable
fun StatusBadge(text: String) {
    val p = Palette
    Text(
        text.uppercase(),
        fontSize = 10.sp,
        fontWeight = FontWeight.SemiBold,
        letterSpacing = 0.6.sp,
        color = p.status,
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(p.status.copy(alpha = 0.12f))
            .border(1.dp, p.status.copy(alpha = 0.35f), RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 4.dp),
    )
}

@Composable
fun SimulatedBadge() {
    val p = Palette
    Text(
        "SIMULADO",
        fontSize = 9.sp,
        fontWeight = FontWeight.SemiBold,
        letterSpacing = 0.6.sp,
        color = p.gold,
        modifier = Modifier
            .border(1.dp, p.gold.copy(alpha = 0.45f), RoundedCornerShape(50))
            .padding(horizontal = 7.dp, vertical = 3.dp),
    )
}

@Composable
fun InitialsAvatar(initials: String, size: Dp = 44.dp) {
    val p = Palette
    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .background(p.gold.copy(alpha = 0.12f))
            .border(1.dp, p.gold.copy(alpha = 0.55f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            initials,
            fontSize = (size.value * 0.36f).sp,
            fontWeight = FontWeight.SemiBold,
            color = p.gold,
        )
    }
}

@Composable
fun ShortcutButton(title: String, icon: ImageVector, onClick: () -> Unit) {
    val p = Palette
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(56.dp)
                .clip(CircleShape)
                .background(p.gold.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = title, tint = p.gold, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.height(8.dp))
        Text(
            title,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
            color = p.ivory,
            textAlign = TextAlign.Center,
            maxLines = 2,
            modifier = Modifier.height(28.dp),
        )
    }
}

@Composable
fun LimitBar(ratio: Double) {
    val p = Palette
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(6.dp)
            .clip(RoundedCornerShape(50))
            .background(p.line),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(ratio.toFloat().coerceIn(0.04f, 1f))
                .height(6.dp)
                .clip(RoundedCornerShape(50))
                .background(p.gold),
        )
    }
}

@Composable
fun SectionTitle(text: String) {
    Text(text, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = Palette.ivory)
}

@Composable
fun SettingsRow(
    icon: ImageVector,
    title: String,
    subtitle: String? = null,
    onClick: () -> Unit,
) {
    val p = Palette
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Icon(icon, contentDescription = null, tint = p.gold, modifier = Modifier.size(22.dp).padding(top = 2.dp))
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(title, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
            if (subtitle != null) {
                Text(subtitle, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = p.mute)
            }
        }
        Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null, tint = p.mute, modifier = Modifier.size(16.dp))
    }
}

@Composable
fun PlasticCard(card: MockCard, modifier: Modifier = Modifier) {
    val p = Palette
    val colors = when (card.theme) {
        MockCard.Theme.BLACK -> listOf(hex("#1A1A1C"), hex("#0D0D0E"))
        MockCard.Theme.PLATINUM -> listOf(hex("#2A2A2E"), hex("#141416"))
        MockCard.Theme.VIRTUAL -> listOf(hex("#161618"), hex("#0B0B0C"))
    }
    Column(
        modifier = modifier
            .fillMaxWidth()
            .height(176.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(Brush.linearGradient(colors))
            .border(1.dp, p.gold.copy(alpha = 0.35f), RoundedCornerShape(16.dp))
            .padding(18.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Row {
                Text("Bank", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                Text("Core", color = p.gold, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            }
            Text(
                card.name.uppercase(),
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 0.8.sp,
                color = p.gold,
            )
        }
        Text(
            Money.reais(card.invoice),
            fontSize = 26.sp,
            fontWeight = FontWeight.SemiBold,
            fontFamily = FontFamily.Monospace,
            color = Color.White,
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text("Vencimento", fontSize = 11.sp, color = p.mute)
                Text(card.dueLabel, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = Color.White)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("Compras", fontSize = 11.sp, color = p.mute)
                Text(card.period, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = Color.White)
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("•••• ${card.last4}", fontSize = 13.sp, fontFamily = FontFamily.Monospace, color = Color.White.copy(alpha = 0.8f))
            Text(card.brand.uppercase(), fontSize = 11.sp, fontWeight = FontWeight.Bold, color = p.mute)
        }
    }
}

@Composable
fun Hairline() {
    Box(Modifier.fillMaxWidth().height(1.dp).background(Palette.line))
}
