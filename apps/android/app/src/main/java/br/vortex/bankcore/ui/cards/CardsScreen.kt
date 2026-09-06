package br.vortex.bankcore.ui.cards

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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.Hub
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.Hairline
import br.vortex.bankcore.ui.components.LimitBar
import br.vortex.bankcore.ui.components.PlasticCard
import br.vortex.bankcore.ui.components.SectionTitle
import br.vortex.bankcore.ui.components.SimulatedBadge
import br.vortex.bankcore.ui.components.Wordmark
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.Money

@Composable
fun CardsScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    val mock = vm.mock
    val pager = rememberPagerState(pageCount = { mock.cards.size })
    val current = mock.cards.getOrNull(pager.currentPage) ?: mock.primaryCard

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(p.ink)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) { Wordmark(16) }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionTitle("Cartões")
            SimulatedBadge()
        }
        Text("Módulo didático. Fatura e limite não liquidam no ledger BankCore.", fontSize = 12.sp, color = p.mute)

        CarbonCard {
            Row(Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        if (state.isBalanceHidden) "••••••" else Money.reais(current.used),
                        fontSize = 22.sp,
                        fontWeight = FontWeight.SemiBold,
                        fontFamily = FontFamily.Monospace,
                        color = p.ivory,
                    )
                    Text("Limite utilizado", fontSize = 11.sp, color = p.mute)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        if (state.isBalanceHidden) "••••••" else Money.reais(current.available),
                        fontSize = 22.sp,
                        fontWeight = FontWeight.SemiBold,
                        fontFamily = FontFamily.Monospace,
                        color = p.ivory,
                    )
                    Text("Disponível", fontSize = 11.sp, color = p.mute)
                }
            }
            Spacer(Modifier.height(10.dp))
            LimitBar(current.usedRatio)
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Total ${Money.reais(current.total)}", fontSize = 11.sp, fontFamily = FontFamily.Monospace, color = p.mute)
                Text("Renovação 10/Set", fontSize = 11.sp, fontFamily = FontFamily.Monospace, color = p.mute)
            }
        }

        HorizontalPager(state = pager, modifier = Modifier.height(210.dp)) { index ->
            PlasticCard(mock.cards[index], modifier = Modifier.padding(horizontal = 4.dp))
        }

        Row(Modifier.fillMaxWidth()) {
            CardAction("Pagar fatura", Icons.Outlined.Payments, Modifier.weight(1f)) { vm.openHub(Hub.Invoice) }
            CardAction("Carteira", Icons.Outlined.AccountBalanceWallet, Modifier.weight(1f)) {
                vm.simulate("Simulação: Google Wallet. Não grava no ledger.")
            }
            CardAction("Virtual", Icons.Outlined.CreditCard, Modifier.weight(1f)) {
                vm.simulate("Cartão virtual gerado (UX). Não grava no ledger.")
            }
            CardAction("Bloquear", Icons.Outlined.Lock, Modifier.weight(1f)) {
                vm.simulate("Simulação: cartão bloqueado/desbloqueado.")
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Últimos lançamentos", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.weight(1f))
            Text("Fatura atual · Set", fontSize = 11.sp, color = p.mute)
        }
        CarbonCard(padding = 8.dp) {
            mock.cardPurchases.forEachIndexed { index, item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(item.merchant, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                        Text(item.detail, fontSize = 11.sp, color = p.mute)
                    }
                    Text(Money.reais(item.amount), fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace, color = p.debit)
                }
                if (index != mock.cardPurchases.lastIndex) Hairline()
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun CardAction(title: String, icon: ImageVector, modifier: Modifier, onClick: () -> Unit) {
    val p = Palette
    Column(
        modifier = modifier.clickable(onClick = onClick).padding(4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(
            icon,
            contentDescription = title,
            tint = p.gold,
            modifier = Modifier
                .size(40.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(p.gold.copy(alpha = 0.12f))
                .padding(10.dp),
        )
        Text(title, fontSize = 10.sp, fontWeight = FontWeight.Medium, color = p.ivory, textAlign = TextAlign.Center, maxLines = 2)
    }
}
