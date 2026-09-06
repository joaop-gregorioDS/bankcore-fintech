package br.vortex.bankcore.ui.login

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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.PersonAdd
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.data.ApiConfig
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.BrandMark
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.CarbonField
import br.vortex.bankcore.ui.components.DemoBanner
import br.vortex.bankcore.ui.components.GoldButton
import br.vortex.bankcore.ui.components.InitialsAvatar
import br.vortex.bankcore.ui.components.VersionLabel
import br.vortex.bankcore.ui.components.Wordmark
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.TaxId

@Composable
fun LoginScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    var modeLogin by remember { mutableStateOf(true) }
    var taxId by remember { mutableStateOf(state.lastTaxId.orEmpty()) }
    var password by remember { mutableStateOf("") }
    var fullName by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var showForm by remember { mutableStateOf(false) }

    val preferred = if (state.lastTaxId == ApiConfig.maria.taxId) ApiConfig.maria else ApiConfig.lucas

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(p.ink)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        Spacer(Modifier.height(8.dp))
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
            BrandMark(56.dp)
            Wordmark(34)
            Text(
                "Banking de demonstração · ${ApiConfig.LEGAL_NAME}",
                fontSize = 15.sp,
                color = p.mute,
            )
            DemoBanner()
            VersionLabel(Modifier.padding(top = 4.dp))
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(p.card)
                .border(1.dp, p.gold.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
                .clickable(enabled = !state.isBusy) { vm.loginDemo(preferred) }
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            InitialsAvatar(initials(preferred.name), 48.dp)
            Spacer(Modifier.size(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(preferred.name, fontSize = 17.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                Text(
                    "Ag. 0001-9 · ${TaxId.formatted(preferred.taxId)}",
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace,
                    color = p.mute,
                )
            }
            Icon(Icons.Outlined.PersonAdd, contentDescription = null, tint = p.gold, modifier = Modifier.size(22.dp))
        }

        Row(Modifier.fillMaxWidth()) {
            Text(
                "Trocar conta",
                modifier = Modifier
                    .weight(1f)
                    .clickable { showForm = true }
                    .padding(vertical = 8.dp),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = p.ivory,
            )
            Text(
                "Fazer Pix",
                modifier = Modifier
                    .weight(1f)
                    .clickable(enabled = !state.isBusy) { vm.loginDemoAndOpenPix(preferred) }
                    .padding(vertical = 8.dp),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = p.gold,
            )
        }

        CarbonCard {
            Text("Contas de demonstração", fontSize = 12.sp, fontWeight = FontWeight.Medium, color = p.mute)
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                DemoChip(ApiConfig.lucas, "LM", !state.isBusy, Modifier.weight(1f)) {
                    taxId = ApiConfig.lucas.taxId
                    password = ApiConfig.lucas.password
                    modeLogin = true
                    vm.loginDemo(ApiConfig.lucas)
                }
                DemoChip(ApiConfig.maria, "MS", !state.isBusy, Modifier.weight(1f)) {
                    taxId = ApiConfig.maria.taxId
                    password = ApiConfig.maria.password
                    modeLogin = true
                    vm.loginDemo(ApiConfig.maria)
                }
            }
        }

        CarbonCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Pix real entre Lucas e Maria", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                    Text(
                        "O avaliador entra, transfere R$ 1,00 e vê o comprovante no ledger interno.",
                        fontSize = 12.sp,
                        color = p.mute,
                    )
                }
                Text(
                    "Simular",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = p.onGold,
                    modifier = Modifier
                        .clip(RoundedCornerShape(50))
                        .background(p.gold)
                        .clickable(enabled = !state.isBusy) { vm.loginDemoAndOpenPix(preferred) }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                )
            }
        }

        if (showForm) {
            CarbonCard(padding = 20.dp) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(p.input)
                        .border(1.dp, p.line, RoundedCornerShape(8.dp))
                        .padding(4.dp),
                ) {
                    ModeTab("Acessar conta", modeLogin, Modifier.weight(1f)) {
                        modeLogin = true
                        vm.clearError()
                    }
                    ModeTab("Abrir conta", !modeLogin, Modifier.weight(1f)) {
                        modeLogin = false
                        vm.clearError()
                    }
                }
                Spacer(Modifier.height(16.dp))
                if (modeLogin) {
                    CarbonField("CPF do correntista", taxId, { taxId = it }, placeholder = "00000000000", keyboardType = KeyboardType.Number, mono = true)
                    Spacer(Modifier.height(12.dp))
                    CarbonField("Senha de acesso", password, { password = it }, placeholder = "••••••••", isSecure = true)
                    Spacer(Modifier.height(16.dp))
                    GoldButton(
                        title = "Entrar",
                        icon = Icons.AutoMirrored.Outlined.ArrowForward,
                        isLoading = state.isBusy,
                        enabled = TaxId.digits(taxId).length >= 11 && password.length >= 8,
                    ) { vm.login(taxId, password) }
                } else {
                    CarbonField("Nome completo", fullName, { fullName = it }, placeholder = "Nome e sobrenome")
                    Spacer(Modifier.height(12.dp))
                    CarbonField("CPF (apenas números)", taxId, { taxId = it }, placeholder = "00000000000", keyboardType = KeyboardType.Number, mono = true)
                    Spacer(Modifier.height(12.dp))
                    CarbonField("E-mail", email, { email = it }, placeholder = ApiConfig.CONTACT_EMAIL, keyboardType = KeyboardType.Email)
                    Spacer(Modifier.height(12.dp))
                    CarbonField("Senha (mínimo 8)", password, { password = it }, placeholder = "••••••••", isSecure = true)
                    Spacer(Modifier.height(16.dp))
                    GoldButton(
                        title = "Criar conta",
                        icon = Icons.Outlined.Check,
                        isLoading = state.isBusy,
                        enabled = TaxId.digits(taxId).length >= 11 && password.length >= 8 &&
                            fullName.trim().length >= 3 && email.contains("@"),
                    ) { vm.register(taxId, fullName, email, password) }
                }
                state.errorMessage?.let {
                    Spacer(Modifier.height(12.dp))
                    Text(it, fontSize = 12.sp, color = p.debit, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun ModeTab(title: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val p = Palette
    Text(
        title,
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (selected) p.gold else androidx.compose.ui.graphics.Color.Transparent)
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        fontSize = 13.sp,
        fontWeight = FontWeight.SemiBold,
        color = if (selected) p.onGold else p.mute,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@Composable
private fun DemoChip(
    demo: ApiConfig.DemoAccount,
    initials: String,
    enabled: Boolean,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    val p = Palette
    Row(
        modifier = modifier
            .border(1.dp, p.line, RoundedCornerShape(10.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        InitialsAvatar(initials, 36.dp)
        Spacer(Modifier.size(10.dp))
        Column {
            Text(demo.name.split(" ").take(2).joinToString(" "), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
            Text(TaxId.formatted(demo.taxId), fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = p.mute, maxLines = 1)
        }
    }
}

private fun initials(name: String): String =
    name.split(" ").take(2).mapNotNull { it.firstOrNull() }.joinToString("").uppercase()
