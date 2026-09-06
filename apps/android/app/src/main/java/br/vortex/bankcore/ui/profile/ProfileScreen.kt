package br.vortex.bankcore.ui.profile

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Accessibility
import androidx.compose.material.icons.outlined.Devices
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.QrCode
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.vortex.bankcore.data.ApiConfig
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.BrandMark
import br.vortex.bankcore.ui.components.Hairline
import br.vortex.bankcore.ui.components.InitialsAvatar
import br.vortex.bankcore.ui.components.SectionTitle
import br.vortex.bankcore.ui.components.SettingsRow
import br.vortex.bankcore.ui.components.VersionLabel
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.util.BankDate

@Composable
fun ProfileScreen(vm: BankCoreViewModel, state: UiState) {
    val p = Palette
    val mock = vm.mock

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(p.ink)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp),
    ) {
        Text("Meu Perfil", fontSize = 22.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            InitialsAvatar(mock.initials, 56.dp)
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(state.session?.fullName ?: "Correntista", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                Text(
                    "Ag. ${mock.agency} · Cc. ${state.account?.accountNumber ?: "—"}",
                    fontSize = 13.sp,
                    fontFamily = FontFamily.Monospace,
                    color = p.mute,
                )
                Text("Visto em ${BankDate.display(state.lastSeen)}", fontSize = 11.sp, color = p.mute)
                Text(mock.segment, fontSize = 11.sp, color = p.gold)
            }
        }

        Column {
            SectionTitle("Configurações")
            Spacer(Modifier.height(8.dp))
            Row(
                Modifier.fillMaxWidth().padding(vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("Modo escuro", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                    Text("O app abre no modo claro. Ative só se quiser a paleta carbon.", fontSize = 12.sp, color = p.mute)
                }
                Switch(
                    checked = state.usesDarkAppearance,
                    onCheckedChange = { vm.setDarkAppearance(it) },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = p.onGold,
                        checkedTrackColor = p.gold,
                        uncheckedThumbColor = p.mute,
                        uncheckedTrackColor = p.line,
                    ),
                )
            }
            Hairline()
            SettingsRow(Icons.Outlined.Settings, "Geral", "Notificações, acesso ao app e preferências da tela de login.") {
                vm.simulate("Simulação: ajustes gerais.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.Group, "Cadastro", "Nome, e-mail e telefone. Os dados reais vêm de GET /auth/me.") {
                vm.simulate("Cadastro é leitura da API. Edição é UX simulada.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.Shield, "Privacidade", "Ledger interno de demonstração. Não há SPI/DICT.") {
                vm.simulate("Documento de portfólio · ${ApiConfig.LEGAL_NAME}.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.Accessibility, "Acessibilidade", "Saldo ocultável e números tabulares já ativos neste app.") {
                vm.simulate("Acessibilidade: ocultar saldo no Início.")
            }
        }

        Column {
            SectionTitle("Segurança")
            Spacer(Modifier.height(8.dp))
            SettingsRow(Icons.Outlined.Lock, "Central de Segurança", "JWT no EncryptedSharedPreferences / Android Keystore.") {
                vm.simulate("Token fica no Keystore. Sem SharedPreferences em claro.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.Key, "Central de Senhas") {
                vm.simulate("Troca de senha não está no contrato da API v1.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.QrCode, "BankCore Code", "Habilitado · simulado.") {
                vm.simulate("Código de autorização ilustrativo.")
            }
            Hairline()
            SettingsRow(Icons.Outlined.Devices, "Dispositivos", "Gerenciar liberações (UX).") {
                vm.simulate("Lista de dispositivos é simulada.")
            }
        }

        Column {
            SectionTitle("Sobre o app")
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth().padding(vertical = 12.dp), verticalAlignment = Alignment.Top) {
                androidx.compose.material3.Icon(
                    Icons.Outlined.Info,
                    contentDescription = null,
                    tint = p.gold,
                    modifier = Modifier.padding(top = 2.dp, end = 12.dp),
                )
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("BankCore Android", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = p.ivory)
                    Text("version 1.10.25", fontSize = 13.sp, fontWeight = FontWeight.Medium, fontFamily = FontFamily.Monospace, color = p.gold)
                    Text("${ApiConfig.LEGAL_NAME} · bundle br.vortex.bankcore", fontSize = 11.sp, color = p.mute)
                }
                BrandMark(36.dp)
            }
        }

        Text(
            "SAIR DO APP",
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = 0.8.sp,
            color = p.debit,
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(p.debit.copy(alpha = 0.12f))
                .clickable { vm.logout() }
                .padding(vertical = 14.dp),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )

        VersionLabel(Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
    }
}
