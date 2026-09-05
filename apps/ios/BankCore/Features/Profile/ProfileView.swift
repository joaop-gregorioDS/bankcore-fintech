import SwiftUI

struct ProfileView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    identity
                    VStack(alignment: .leading, spacing: 0) {
                        SectionTitle(text: "Configurações")
                            .padding(.bottom, 8)
                        SettingsRow(icon: "gearshape", title: "Geral", subtitle: "Notificações, acesso ao app e preferências da tela de login.") {
                            app.simulate("Simulação: ajustes gerais.")
                        }
                        divider
                        SettingsRow(icon: "person.2", title: "Cadastro", subtitle: "Nome, e-mail e telefone. Os dados reais vêm de GET /auth/me.") {
                            app.simulate("Cadastro é leitura da API. Edição é UX simulada.")
                        }
                        divider
                        SettingsRow(icon: "checkmark.shield", title: "Privacidade", subtitle: "Ledger interno de demonstração. Não há SPI/DICT.") {
                            app.simulate("Documento de portfólio · Vortex Software.")
                        }
                        divider
                        SettingsRow(icon: "accessibility", title: "Acessibilidade", subtitle: "Saldo ocultável e números tabulares já ativos neste app.") {
                            app.simulate("Acessibilidade: ocultar saldo no Início.")
                        }
                    }

                    VStack(alignment: .leading, spacing: 0) {
                        SectionTitle(text: "Segurança")
                            .padding(.bottom, 8)
                        SettingsRow(icon: "lock.shield", title: "Central de Segurança", subtitle: "JWT no Keychain deste aparelho.") {
                            app.simulate("Token fica no Keychain. Sem UserDefaults.")
                        }
                        divider
                        SettingsRow(icon: "key", title: "Central de Senhas") {
                            app.simulate("Troca de senha não está no contrato da API v1.")
                        }
                        divider
                        SettingsRow(icon: "qrcode", title: "BankCore Code", subtitle: "Habilitado · simulado.") {
                            app.simulate("Código de autorização ilustrativo.")
                        }
                        divider
                        SettingsRow(icon: "iphone.and.arrow.forward", title: "Dispositivos", subtitle: "Gerenciar liberações (UX).") {
                            app.simulate("Lista de dispositivos é simulada.")
                        }
                    }

                    VStack(alignment: .leading, spacing: 0) {
                        SectionTitle(text: "Sobre o app")
                            .padding(.bottom, 8)
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: "info.circle")
                                .font(.system(size: 18, weight: .medium))
                                .foregroundStyle(Palette.gold)
                                .frame(width: 28)
                                .padding(.top, 2)
                            VStack(alignment: .leading, spacing: 4) {
                                Text("BankCore iOS")
                                    .font(.system(size: 16, weight: .semibold))
                                    .foregroundStyle(Palette.ivory)
                                Text(AppVersion.line)
                                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                                    .foregroundStyle(Palette.gold)
                                Text("Vortex Software · bundle br.vortex.bankcore")
                                    .font(TypeScale.micro)
                                    .foregroundStyle(Palette.mute)
                            }
                            Spacer()
                            BrandMark(size: 36)
                        }
                        .padding(.vertical, 12)
                    }

                    Button {
                        app.logout()
                    } label: {
                        Text("SAIR DO APP")
                            .font(TypeScale.cta)
                            .tracking(0.8)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .foregroundStyle(Palette.debit)
                            .background(Palette.debit.opacity(0.12))
                            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 8)

                    VersionLabel()
                        .frame(maxWidth: .infinity)
                        .padding(.top, 4)
                }
                .padding(16)
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationTitle("Meu Perfil")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var identity: some View {
        HStack(spacing: 14) {
            InitialsAvatar(initials: app.mock.initials, size: 56)
            VStack(alignment: .leading, spacing: 4) {
                Text(app.session?.fullName ?? "Correntista")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Palette.ivory)
                Text("Ag. \(app.mock.agency) · Cc. \(app.account?.accountNumber ?? "—")")
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(Palette.mute)
                Text("Visto em \(BankDate.display(app.lastSeen))")
                    .font(TypeScale.micro)
                    .foregroundStyle(Palette.mute)
                Text(app.mock.segment)
                    .font(TypeScale.micro)
                    .foregroundStyle(Palette.gold)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var divider: some View {
        Rectangle().fill(Palette.line).frame(height: 1)
    }
}
