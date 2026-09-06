package br.vortex.bankcore.ui.statement

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ReceiptLong
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.CarbonCard
import br.vortex.bankcore.ui.components.TransactionRow
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.Money

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatementScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    val income = state.statement.filter { it.isCredit }.sumOf { it.amountReais }
    val expense = state.statement.filter { !it.isCredit }.sumOf { it.amountReais }
    var refreshing by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().background(p.ink)) {
        Text(
            "Extrato",
            fontSize = 22.sp,
            fontWeight = FontWeight.SemiBold,
            color = p.ivory,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
        )
        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = {
                refreshing = true
                vm.refresh()
                refreshing = false
            },
            modifier = Modifier.fillMaxSize(),
        ) {
            if (state.statement.isEmpty()) {
                Column(
                    Modifier.fillMaxSize(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(Icons.Outlined.ReceiptLong, contentDescription = null, tint = p.mute)
                    Spacer(Modifier.height(8.dp))
                    Text("Sem lançamentos", fontWeight = FontWeight.SemiBold, color = p.mute)
                    Text("Pix e depósitos do ledger aparecem aqui.", fontSize = 12.sp, color = p.mute)
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                    item {
                        CarbonCard {
                            Row(Modifier.fillMaxWidth()) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text("Entradas", fontSize = 11.sp, color = p.mute)
                                    Text(Money.signed(income, credit = true), fontWeight = FontWeight.SemiBold, color = p.ivory)
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("Saídas", fontSize = 11.sp, color = p.mute)
                                    Text(Money.signed(expense, credit = false), fontWeight = FontWeight.SemiBold, color = p.debit)
                                }
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                    }
                    items(state.statement, key = { it.transactionId }) { tx ->
                        TransactionRow(tx) { vm.openReceipt(tx) }
                    }
                    item { Spacer(Modifier.height(24.dp)) }
                }
            }
        }
    }
}
