package br.vortex.bankcore.ui.hubs

import androidx.compose.foundation.background
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
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.QrCode
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material.icons.outlined.Sync
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.Hub
import br.vortex.bankcore.ui.MainTab
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.GoldButton
import br.vortex.bankcore.ui.components.SectionTitle
import br.vortex.bankcore.ui.components.SimulatedBadge
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.Money

@Composable
fun HubSheet(hub: Hub, vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    Column(Modifier.fillMaxSize().background(p.ink)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = { vm.dismissHub() }) { Text("Fechar", color = p.gold) }
        }
        when (hub) {
            Hub.Pay -> PayHub(vm)
            Hub.Dda -> DdaHub(vm)
            Hub.Invest -> InvestHub(vm)
            Hub.Credit -> CreditHub(vm)
            Hub.More -> MoreHub(vm)
            Hub.Notifications -> NotificationsHub(vm)
            Hub.Invoice -> InvoiceHub(vm)
        }
    }
}

@Composable
private fun HubHeader(title: String, subtitle: String) {
    val p = Palette
    Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle(title)
            SimulatedBadge()
        }
        Text(subtitle, fontSize = 12.sp, color = p.mute)
    }
}

@Composable
private fun PayHub(vm: BankCoreViewModel) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        HubHeader("Pagar", "Boletos, tributos e DDA são simulação de UX. Só Pix e depósito gravam no ledger.")
        Tile("Pix", Icons.Outlined.SwapHoriz, "Ledger real · CPF de outro correntista.") {
            vm.dismissHub()
            vm.selectTab(MainTab.Pix)
        }
        Tile("Boleto", Icons.Outlined.QrCode, "Linha digitável ilustrativa.") {
            vm.simulate("Simulação: boleto não altera o ledger.")
        }
        Tile("Agenda DDA", Icons.Outlined.DateRange, "${vm.mock.dda.size} títulos · ${Money.reais(vm.mock.scheduledTotal)}") {
            vm.openHub(Hub.Dda)
        }
        Tile("Débito automático", Icons.Outlined.Sync, "Gestão ilustrativa.") {
            vm.simulate("Débito automático é UX simulada.")
        }
    }
}

@Composable
private fun DdaHub(vm: BankCoreViewModel) {
    val p = Palette
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle("Agenda DDA")
            SimulatedBadge()
        }
        CarbonCard {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Total agendado", color = p.ivory)
                Text(Money.reais(vm.mock.scheduledTotal), fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.debit)
            }
        }
        Text("Boletos eletrônicos", fontSize = 12.sp, color = p.mute)
        vm.mock.dda.forEach { bill ->
            CarbonCard {
                Row(
                    Modifier.fillMaxWidth().clickable {
                        vm.simulate("Simulação: ${bill.payee} · ${Money.reais(bill.amount)} não liquida no ledger.")
                    },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(bill.payee, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                        Text("Vence ${bill.due}", fontSize = 11.sp, color = p.mute)
                    }
                    Text(Money.reais(bill.amount), fontWeight = FontWeight.SemiBold, color = p.ivory)
                }
            }
        }
    }
}

@Composable
private fun InvestHub(vm: BankCoreViewModel) {
    val p = Palette
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle("BankCore Invest")
            SimulatedBadge()
        }
        Text("Posição ilustrativa. CDB e Tesouro não liquidam no ledger.", fontSize = 12.sp, color = p.mute)
        CarbonCard {
            Text("Patrimônio", fontSize = 12.sp, color = p.mute)
            Text(Money.reais(vm.mock.investTotal), fontSize = 32.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.ivory)
        }
        vm.mock.investments.forEach { item ->
            CarbonCard {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(item.name, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                        Text(item.yield, fontSize = 11.sp, color = p.status)
                    }
                    Text(Money.reais(item.amount), fontWeight = FontWeight.SemiBold, color = p.ivory)
                }
            }
        }
        GoldButton(title = "Simular aplicação") {
            vm.simulate("Simulação: aplicação de R$ 100/mês. Não grava no ledger.")
        }
    }
}

@Composable
private fun CreditHub(vm: BankCoreViewModel) {
    val p = Palette
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle("Crédito")
            SimulatedBadge()
        }
        Text("Tabela Price ilustrativa. Empréstimo não liquida no ledger.", fontSize = 12.sp, color = p.mute)
        CarbonCard {
            Text("Limite pré-aprovado", fontSize = 12.sp, color = p.mute)
            Text(Money.reais(vm.mock.creditLimit), fontSize = 32.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.ivory)
            Text("Segmento ${vm.mock.segment}", fontSize = 11.sp, color = p.gold)
        }
        CarbonCard {
            CreditRow("Valor ilustrativo", Money.reais(10_000.0))
            CreditRow("Prazo", "24 meses")
            CreditRow("CET a.m.", "1,79%")
            CreditRow("Parcela", Money.reais(512.40))
        }
        GoldButton(title = "Simular contratação") {
            vm.simulate("Simulação: crédito Tabela Price. Não grava no ledger.")
        }
    }
}

@Composable
private fun CreditRow(k: String, v: String) {
    val p = Palette
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(k, fontSize = 12.sp, color = p.mute)
        Text(v, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
    }
}

@Composable
private fun MoreHub(vm: BankCoreViewModel) {
    val p = Palette
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionTitle("Ver mais")
        Tile("Pix (ledger real)", Icons.Outlined.SwapHoriz, null) {
            vm.dismissHub()
            vm.selectTab(MainTab.Pix)
        }
        Tile("Extrato (ledger real)", Icons.Outlined.Description, null) {
            vm.dismissHub()
            vm.selectTab(MainTab.Statement)
        }
        Text("Simulado", fontSize = 12.sp, color = p.mute, modifier = Modifier.padding(top = 8.dp))
        Tile("Cartões", Icons.Outlined.CreditCard, null) { vm.dismissHub(); vm.selectTab(MainTab.Cards) }
        Tile("Agenda DDA", Icons.Outlined.DateRange, null) { vm.openHub(Hub.Dda) }
        Tile("BankCore Invest", Icons.Outlined.ShowChart, null) { vm.openHub(Hub.Invest) }
        Tile("Crédito", Icons.Outlined.AccountBalanceWallet, null) { vm.openHub(Hub.Credit) }
        Tile("Cobranças PJ", Icons.Outlined.Description, null) { vm.simulate("Cobranças PJ são UX simulada.") }
    }
}

@Composable
private fun NotificationsHub(vm: BankCoreViewModel) {
    val p = Palette
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionTitle("Notificações")
        vm.mock.notifications.forEach { item ->
            CarbonCard {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text(item.title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.weight(1f, fill = false))
                            if (item.simulated) SimulatedBadge()
                        }
                        Text(item.body, fontSize = 12.sp, color = p.mute)
                        Text(item.time, fontSize = 11.sp, color = p.mute)
                    }
                }
            }
        }
    }
}

@Composable
private fun InvoiceHub(vm: BankCoreViewModel) {
    val p = Palette
    val card = vm.mock.primaryCard
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle("Fatura")
            SimulatedBadge()
        }
        CarbonCard {
            Text(card.name, fontSize = 12.sp, color = p.mute)
            Text(Money.reais(card.invoice), fontSize = 32.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.ivory)
            Text("Vencimento ${card.dueLabel} · ${card.period}", fontSize = 12.sp, color = p.mute)
        }
        Text("Módulo didático. Esta fatura não liquida no ledger BankCore.", fontSize = 12.sp, color = p.mute)
        GoldButton(title = "Pagar fatura (simulado)") {
            vm.simulate("Simulação: pagamento de fatura. Não altera o saldo do ledger.")
        }
    }
}

@Composable
private fun Tile(title: String, icon: ImageVector, subtitle: String?, onClick: () -> Unit) {
    val p = Palette
    CarbonCard {
        Row(
            Modifier.fillMaxWidth().clickable(onClick = onClick),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = p.gold,
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(p.gold.copy(alpha = 0.12f))
                    .padding(8.dp),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                if (subtitle != null) Text(subtitle, fontSize = 12.sp, color = p.mute)
            }
            Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null, tint = p.mute)
        }
    }
}
