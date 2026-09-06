package br.vortex.bankcore.ui.home

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.MoreHoriz
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.QrCode
import androidx.compose.material.icons.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material.icons.outlined.AccountBalanceWallet
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.Hub
import br.vortex.bankcore.ui.MainTab
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.BrandMark
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.Hairline
import br.vortex.bankcore.ui.components.LimitBar
import br.vortex.bankcore.ui.components.PlasticCard
import br.vortex.bankcore.ui.components.SectionTitle
import br.vortex.bankcore.ui.components.ShortcutButton
import br.vortex.bankcore.ui.components.SimulatedBadge
import br.vortex.bankcore.ui.components.StatusBadge
import br.vortex.bankcore.ui.components.TransactionRow
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.Money
import br.vortex.bankcore.util.TaxId

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    val mock = vm.mock
    val context = LocalContext.current
    var refreshing by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().background(p.ink)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(p.panel)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BrandMark(28.dp)
            Spacer(Modifier.size(10.dp))
            Text("Olá, ${mock.firstName}", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.weight(1f))
            Icon(
                if (state.isBalanceHidden) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                contentDescription = "Ocultar saldo",
                tint = p.ivory,
                modifier = Modifier.size(32.dp).clickable { vm.toggleBalanceHidden() }.padding(4.dp),
            )
            Box(modifier = Modifier.clickable { vm.openHub(Hub.Notifications) }) {
                Icon(Icons.Outlined.Notifications, contentDescription = "Notificações", tint = p.ivory, modifier = Modifier.size(32.dp).padding(4.dp))
                Text(
                    "${mock.notifications.size}",
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Bold,
                    color = p.onGold,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .clip(CircleShape)
                        .background(p.gold)
                        .padding(horizontal = 4.dp, vertical = 1.dp),
                )
            }
        }
        Hairline()

        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = {
                refreshing = true
                vm.refresh()
                refreshing = false
            },
            modifier = Modifier.fillMaxSize(),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
            ) {
                CarbonCard {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Saldo", fontSize = 12.sp, color = p.mute)
                            Text(
                                hidden(state.isBalanceHidden, state.account?.balanceReais ?: 0.0),
                                fontSize = 28.sp,
                                fontWeight = FontWeight.SemiBold,
                                fontFamily = FontFamily.Monospace,
                                color = p.ivory,
                            )
                            Row(
                                modifier = Modifier.padding(top = 4.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                            ) {
                                Text(
                                    "Cc. ${state.account?.accountNumber ?: "—"}",
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = p.mute,
                                )
                                if (state.account?.isActive == true) StatusBadge("Ativa")
                            }
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                                Text("Agendado", fontSize = 12.sp, color = p.mute)
                                SimulatedBadge()
                            }
                            Text(
                                if (state.isBalanceHidden) "••••••" else Money.signed(mock.scheduledTotal, credit = false),
                                fontSize = 20.sp,
                                fontWeight = FontWeight.SemiBold,
                                fontFamily = FontFamily.Monospace,
                                color = p.debit,
                            )
                            Text(
                                "Ver DDA",
                                fontSize = 11.sp,
                                color = p.gold,
                                modifier = Modifier.padding(top = 2.dp).clickable { vm.openHub(Hub.Dda) },
                            )
                        }
                    }
                }

                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(Modifier.fillMaxWidth()) {
                        Box(Modifier.weight(1f)) { ShortcutButton("Extrato", Icons.Outlined.ReceiptLong) { vm.selectTab(MainTab.Statement) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("Pagar", Icons.Outlined.QrCode) { vm.openHub(Hub.Pay) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("Pix", Icons.Outlined.SwapHoriz) { vm.selectTab(MainTab.Pix) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("Investir", Icons.Outlined.ShowChart) { vm.openHub(Hub.Invest) } }
                    }
                    Row(Modifier.fillMaxWidth()) {
                        Box(Modifier.weight(1f)) { ShortcutButton("Cartões", Icons.Outlined.CreditCard) { vm.selectTab(MainTab.Cards) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("Empréstimo", Icons.Outlined.AccountBalanceWallet) { vm.openHub(Hub.Credit) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("DDA", Icons.Outlined.DateRange) { vm.openHub(Hub.Dda) } }
                        Box(Modifier.weight(1f)) { ShortcutButton("Ver mais", Icons.Outlined.MoreHoriz) { vm.openHub(Hub.More) } }
                    }
                }

                CarbonCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                                Text(mock.promoTitle, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.weight(1f, fill = false))
                                SimulatedBadge()
                            }
                            Text(mock.promoBody, fontSize = 12.sp, color = p.mute)
                        }
                        Text(
                            "Simular",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = p.onGold,
                            modifier = Modifier
                                .clip(CircleShape)
                                .background(p.gold)
                                .clickable { vm.openHub(Hub.Invest) }
                                .padding(horizontal = 14.dp, vertical = 8.dp),
                        )
                    }
                }

                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        SectionTitle("Cartões")
                        Spacer(Modifier.size(8.dp))
                        SimulatedBadge()
                        Spacer(Modifier.weight(1f))
                        Text("Ver todos", fontSize = 12.sp, color = p.gold, modifier = Modifier.clickable { vm.selectTab(MainTab.Cards) })
                    }
                    val card = mock.primaryCard
                    CarbonCard {
                        Row(Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(hidden(state.isBalanceHidden, card.used), fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold, color = p.ivory)
                                Text("Limite utilizado", fontSize = 11.sp, color = p.mute)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(hidden(state.isBalanceHidden, card.available), fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold, color = p.ivory)
                                Text("Disponível", fontSize = 11.sp, color = p.mute)
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        LimitBar(card.usedRatio)
                    }
                    val pager = rememberPagerState(pageCount = { mock.cards.size })
                    HorizontalPager(state = pager, modifier = Modifier.height(200.dp)) { index ->
                        PlasticCard(
                            mock.cards[index],
                            modifier = Modifier
                                .padding(horizontal = 2.dp)
                                .clickable { vm.selectTab(MainTab.Cards) },
                        )
                    }
                }

                CarbonCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Chave Pix (CPF)", fontSize = 11.sp, color = p.mute)
                            Text(
                                TaxId.formatted(state.session?.taxId.orEmpty()),
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold,
                                fontFamily = FontFamily.Monospace,
                                color = p.gold,
                            )
                        }
                        Icon(
                            Icons.Outlined.ContentCopy,
                            contentDescription = "Copiar",
                            tint = p.gold,
                            modifier = Modifier
                                .size(32.dp)
                                .clickable {
                                    val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    cm.setPrimaryClip(ClipData.newPlainText("pix", TaxId.digits(state.session?.taxId.orEmpty())))
                                    vm.flash("Chave Pix copiada.")
                                }
                                .padding(4.dp),
                        )
                    }
                }

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Últimos lançamentos", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.weight(1f))
                        Text("Ver extrato →", fontSize = 12.sp, color = p.gold, modifier = Modifier.clickable { vm.selectTab(MainTab.Statement) })
                    }
                    CarbonCard(padding = 8.dp) {
                        if (state.statement.isEmpty()) {
                            Text("Nenhum lançamento no ledger ainda.", fontSize = 12.sp, color = p.mute, modifier = Modifier.padding(12.dp))
                        } else {
                            state.statement.take(4).forEach { tx ->
                                TransactionRow(tx) { vm.openReceipt(tx) }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(24.dp))
            }
        }
    }
}

private fun hidden(hidden: Boolean, value: Double): String =
    if (hidden) "••••••" else Money.reais(value)
