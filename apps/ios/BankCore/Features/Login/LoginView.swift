import SwiftUI

struct LoginView: View {
    @Environment(AppState.self) private var app
    @State private var mode: Mode = .login
    @State private var taxId = ""
    @State private var password = ""
    @State private var fullName = ""
    @State private var email = ""

    private enum Mode { case login, register }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                header
                demoAccounts
                formCard
            }
            .padding(20)
            .padding(.top, 28)
        }
        .background(Palette.ink.ignoresSafeArea())
        .scrollDismissesKeyboard(.interactively)
    }

    private var header: some View {
        VStack(spacing: 12) {
            Image(systemName: "shield")
                .font(.system(size: 22, weight: .medium))
                .foregroundStyle(Palette.gold)
                .frame(width: 48, height: 48)
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(Palette.gold, lineWidth: 1)
                )
            Wordmark()
            Text("Banking de demonstração · Vortex Software")
                .font(TypeScale.body)
                .foregroundStyle(Palette.mute)
            DemoBanner()
        }
        .multilineTextAlignment(.center)
        .frame(maxWidth: .infinity)
    }

    private var demoAccounts: some View {
        CarbonCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Contas de demonstração")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                HStack(spacing: 10) {
                    demoButton(APIConfig.joao)
                    demoButton(APIConfig.maria)
                }
            }
        }
    }

    private func demoButton(_ demo: APIConfig.DemoAccount) -> some View {
        Button {
            taxId = demo.taxId
            password = demo.password
            mode = .login
            Task { await app.loginDemo(demo) }
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(demo.name)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Palette.ivory)
                Text(TaxID.formatted(demo.taxId))
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(Palette.mute)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(Palette.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .disabled(app.isBusy)
    }

    private var formCard: some View {
        CarbonCard(padding: 20) {
            VStack(spacing: 16) {
                HStack(spacing: 4) {
                    modeTab("Acessar conta", .login)
                    modeTab("Abrir conta", .register)
                }
                .padding(4)
                .background(Palette.input)
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Palette.line, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))

                if mode == .login {
                    CarbonField(label: "CPF do correntista", text: $taxId, placeholder: "00000000000", keyboard: .numberPad, mono: true)
                    CarbonField(label: "Senha de acesso", text: $password, placeholder: "••••••••", isSecure: true)
                    GoldButton(title: "Entrar", systemImage: "arrow.right", isLoading: app.isBusy, enabled: canLogin) {
                        Task { await app.login(taxId: taxId, password: password) }
                    }
                } else {
                    CarbonField(label: "Nome completo", text: $fullName, placeholder: "Nome e sobrenome")
                    CarbonField(label: "CPF (apenas números)", text: $taxId, placeholder: "00000000000", keyboard: .numberPad, mono: true)
                    CarbonField(label: "E-mail", text: $email, placeholder: "contato@empresa.com", keyboard: .emailAddress)
                    CarbonField(label: "Senha (mínimo 8)", text: $password, placeholder: "••••••••", isSecure: true)
                    GoldButton(title: "Criar conta", systemImage: "checkmark", isLoading: app.isBusy, enabled: canRegister) {
                        Task {
                            await app.register(taxId: taxId, fullName: fullName, email: email, password: password)
                        }
                    }
                }

                if let errorMessage = app.errorMessage {
                    Text(errorMessage)
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.debit)
                        .frame(maxWidth: .infinity)
                        .multilineTextAlignment(.center)
                }
            }
        }
    }

    private func modeTab(_ title: String, _ value: Mode) -> some View {
        Button {
            mode = value
            app.errorMessage = nil
        } label: {
            Text(title)
                .font(TypeScale.cta)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .foregroundStyle(mode == value ? Palette.ink : Palette.mute)
                .background(mode == value ? Palette.gold : Color.clear)
                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private var canLogin: Bool {
        TaxID.digits(taxId).count >= 11 && password.count >= 8
    }

    private var canRegister: Bool {
        canLogin && fullName.trimmingCharacters(in: .whitespaces).count >= 3 && email.contains("@")
    }
}
