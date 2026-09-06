package br.vortex.bankcore.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import br.vortex.bankcore.ui.cards.CardsScreen
import br.vortex.bankcore.ui.components.BrandMark
import br.vortex.bankcore.ui.components.VersionLabel
import br.vortex.bankcore.ui.components.Wordmark
import br.vortex.bankcore.ui.home.HomeScreen
import br.vortex.bankcore.ui.hubs.HubSheet
import br.vortex.bankcore.ui.login.LoginScreen
import br.vortex.bankcore.ui.pix.PixScreen
import br.vortex.bankcore.ui.profile.ProfileScreen
import br.vortex.bankcore.ui.receipt.ReceiptScreen
import br.vortex.bankcore.ui.statement.StatementScreen
import br.vortex.bankcore.ui.theme.Palette

@Composable
fun BankCoreApp(vm: BankCoreViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    val p = Palette

    Box(Modifier.fillMaxSize().background(p.ink)) {
        when {
            state.isRestoring -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .statusBarsPadding()
                        .background(p.ink),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Spacer(Modifier.height(120.dp))
                    BrandMark(56.dp)
                    Spacer(Modifier.height(16.dp))
                    Wordmark(28)
                    Spacer(Modifier.height(8.dp))
                    VersionLabel()
                    Spacer(Modifier.height(16.dp))
                    CircularProgressIndicator(color = p.gold)
                }
            }
            state.session != null -> {
                Scaffold(
                    containerColor = p.ink,
                    bottomBar = { MainBottomBar(state.selectedTab, vm::selectTab) },
                ) { padding ->
                    Box(Modifier.fillMaxSize().padding(padding).statusBarsPadding()) {
                        when (state.selectedTab) {
                            MainTab.Home -> HomeScreen(vm, state)
                            MainTab.Pix -> PixScreen(vm, state)
                            MainTab.Statement -> StatementScreen(vm, state)
                            MainTab.Cards -> CardsScreen(vm, state)
                            MainTab.Profile -> ProfileScreen(vm, state)
                        }
                    }
                }
            }
            else -> {
                Box(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()) {
                    LoginScreen(vm, state)
                }
            }
        }

        AnimatedVisibility(
            visible = state.toast != null,
            enter = slideInVertically { -it } + fadeIn(),
            exit = slideOutVertically { -it } + fadeOut(),
            modifier = Modifier
                .align(Alignment.TopCenter)
                .statusBarsPadding()
                .padding(top = 56.dp, start = 20.dp, end = 20.dp),
        ) {
            Text(
                state.toast.orEmpty(),
                fontSize = 12.sp,
                color = p.ivory,
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(p.card)
                    .border(1.dp, p.gold.copy(alpha = 0.4f), RoundedCornerShape(10.dp))
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            )
        }
    }

    state.presentedReceipt?.let { tx ->
        Dialog(
            onDismissRequest = { vm.dismissReceipt() },
            properties = DialogProperties(usePlatformDefaultWidth = false),
        ) {
            Box(Modifier.fillMaxSize().background(p.ink).statusBarsPadding().navigationBarsPadding()) {
                ReceiptScreen(vm, state, tx)
            }
        }
    }

    state.presentedHub?.let { hub ->
        Dialog(
            onDismissRequest = { vm.dismissHub() },
            properties = DialogProperties(usePlatformDefaultWidth = false),
        ) {
            Box(Modifier.fillMaxSize().background(p.ink).statusBarsPadding().navigationBarsPadding()) {
                HubSheet(hub, vm, state)
            }
        }
    }
}

@Composable
private fun MainBottomBar(selected: MainTab, onSelect: (MainTab) -> Unit) {
    val p = Palette
    val items = listOf(
        MainTab.Home to ("Início" to Icons.Outlined.Home),
        MainTab.Pix to ("Pix" to Icons.Outlined.SwapHoriz),
        MainTab.Statement to ("Extrato" to Icons.Outlined.ReceiptLong),
        MainTab.Cards to ("Cartões" to Icons.Outlined.CreditCard),
        MainTab.Profile to ("Perfil" to Icons.Outlined.Person),
    )
    NavigationBar(containerColor = p.panel, contentColor = p.gold) {
        items.forEach { (tab, pair) ->
            val (label, icon) = pair
            NavigationBarItem(
                selected = selected == tab,
                onClick = { onSelect(tab) },
                icon = { Icon(icon, contentDescription = label) },
                label = { Text(label, fontSize = 11.sp) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = p.gold,
                    selectedTextColor = p.gold,
                    unselectedIconColor = p.mute,
                    unselectedTextColor = p.mute,
                    indicatorColor = p.gold.copy(alpha = 0.14f),
                ),
            )
        }
    }
}
