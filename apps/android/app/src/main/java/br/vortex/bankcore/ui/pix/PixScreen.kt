package br.vortex.bankcore.ui.pix

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.QrCode
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.data.DirectoryEntry
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.CarbonField
import br.vortex.bankcore.ui.components.GoldButton
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.Money
import br.vortex.bankcore.util.TaxId
import kotlinx.coroutines.launch

@Composable
fun PixScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var destination by remember { mutableStateOf("") }
    var amountText by remember { mutableStateOf("") }
    var descriptionText by remember { mutableStateOf("Pix BankCore") }
    var lookup by remember { mutableStateOf<DirectoryEntry?>(null) }
    var confirming by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }
    var sending by remember { mutableStateOf(false) }

    val parsed = Money.parse(amountText)
    val canContinue = TaxId.digits(destination).length >= 11 && (parsed ?: 0.0) > 0

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(p.ink)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Pix", fontSize = 22.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Pix interno entre correntistas BankCore.", fontSize = 15.sp, color = p.ivory)
            Text("A chave é o CPF só com dígitos. Não é SPI/DICT.", fontSize = 12.sp, color = p.mute)
            Text(
                "Saldo ${if (state.isBalanceHidden) "••••••" else Money.reais(state.account?.balanceReais ?: 0.0)}",
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                fontFamily = FontFamily.Monospace,
                color = p.gold,
                modifier = Modifier.padding(top = 4.dp),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PixChip("Minha chave", Icons.Outlined.Person, Modifier.weight(1f)) {
                val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("pix", TaxId.digits(state.session?.taxId.orEmpty())))
                vm.flash("Chave Pix (CPF) copiada.")
            }
            PixChip("QR Code", Icons.Outlined.QrCode, Modifier.weight(1f)) {
                vm.simulate("Leitor de QR é simulação de UX. Use o CPF da Maria: 12345678900.")
            }
            PixChip("Limites", Icons.Outlined.Tune, Modifier.weight(1f)) {
                vm.simulate("Limite Pix diurno ${Money.reais(vm.mock.pixLimit)} · simulado.")
            }
        }

        CarbonCard(padding = 18.dp) {
            CarbonField("Chave Pix de destino (CPF)", destination, { destination = it }, placeholder = "12345678900", keyboardType = KeyboardType.Number, mono = true)
            Spacer(Modifier.height(14.dp))
            CarbonField("Valor", amountText, { amountText = it }, placeholder = "1,00", keyboardType = KeyboardType.Decimal, mono = true)
            Spacer(Modifier.height(14.dp))
            CarbonField("Descrição", descriptionText, { descriptionText = it }, placeholder = "Pix BankCore")
            Spacer(Modifier.height(14.dp))
            GoldButton(
                title = if (confirming) "Atualizar destinatário" else "Continuar",
                isLoading = sending,
                enabled = canContinue,
            ) {
                scope.launch {
                    localError = null
                    confirming = false
                    sending = true
                    try {
                        lookup = vm.lookupPix(destination)
                        confirming = true
                    } catch (e: Exception) {
                        lookup = null
                        localError = e.message
                    } finally {
                        sending = false
                    }
                }
            }
        }

        if (confirming) {
            lookup?.let { entry ->
                CarbonCard(padding = 18.dp) {
                    Text("Confirmar Pix", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                    Spacer(Modifier.height(12.dp))
                    ConfirmRow("Destinatário", entry.fullName)
                    ConfirmRow("CPF", TaxId.formatted(entry.taxId))
                    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Valor", fontSize = 12.sp, color = p.mute)
                        Text(Money.reais(parsed ?: 0.0), fontSize = 15.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.ivory)
                    }
                    if (descriptionText.isNotBlank()) ConfirmRow("Descrição", descriptionText)
                    Spacer(Modifier.height(8.dp))
                    GoldButton(title = "Confirmar Pix", icon = Icons.Outlined.Check, isLoading = sending) {
                        val amount = parsed ?: return@GoldButton
                        scope.launch {
                            localError = null
                            sending = true
                            try {
                                vm.sendPix(destination, amount, descriptionText.trim())
                                destination = ""
                                amountText = ""
                                descriptionText = "Pix BankCore"
                                lookup = null
                                confirming = false
                            } catch (e: Exception) {
                                localError = e.message
                            } finally {
                                sending = false
                            }
                        }
                    }
                }
            }
        }

        localError?.let { Text(it, fontSize = 12.sp, color = p.debit) }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun PixChip(title: String, icon: androidx.compose.ui.graphics.vector.ImageVector, modifier: Modifier, onClick: () -> Unit) {
    val p = Palette
    Column(
        modifier = modifier
            .background(p.card, RoundedCornerShape(10.dp))
            .border(1.dp, p.line, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(icon, contentDescription = title, tint = p.gold)
        Text(title, fontSize = 11.sp, fontWeight = FontWeight.Medium, color = p.ivory)
    }
}

@Composable
private fun ConfirmRow(label: String, value: String) {
    val p = Palette
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, fontSize = 12.sp, color = p.mute)
        Text(value, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
    }
}
