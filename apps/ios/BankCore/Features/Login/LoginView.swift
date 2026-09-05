import SwiftUI

struct LoginView: View {
    @Environment(AppState.self) private var app
    @State private var mode: Mode = .login
    @State private var taxId = ""
    @State private var password = ""
    @State private var fullName = ""
    @State private var email = ""
    @State private var showForm = false

    private enum Mode { case login, register }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                hero
                lastUserCard
                quickActions
                demoAccounts
                promo
                if showForm { formCard }
            }
            .padding(20)
            .padding(.top, 12)
            .padding(.bottom, 28)
        }
        .background(
            LinearGradient(
                colors: [Color(hex: "#1A1610"), Palette.ink, Palette.ink],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        )
        .scrollDismissesKeyboard(.interactively)
        .onAppear {
            if let last = LastAccountStore.taxId {
                taxId = last
            }
        }
    }

    private var hero: some View {
        VStack(spacing: 14) {
            BrandMark(size: 56)
            VStack(spacing: 8) {
                Wordmark(size: 34)
                Text("Banking de demonstração · Vortex Software")
                    .font(TypeScale.body)
                    .foregroundStyle(Palette.mute)
                DemoBanner()
                VersionLabel()
                    .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 8)
    }

    private var lastUserCard: some View {
        let demo = preferredDemo
        return Button {
            Task { await app.loginDemo(demo) }
        } label: {
            HStack(spacing: 12) {
                InitialsAvatar(initials: initials(demo.name), size: 48)
                VStack(alignment: .leading, spacing: 3) {
                    Text(demo.name)
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Palette.ivory)
                    Text("Ag. 0001-9 · \(TaxID.formatted(demo.taxId))")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(Palette.mute)
                }
                Spacer()
                Image(systemName: "person.crop.rectangle.badge.plus")
                    .font(.system(size: 22))
                    .foregroundStyle(Palette.gold)
            }
            .padding(14)
            .background(Palette.card)
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Palette.gold.opacity(0.35), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(app.isBusy)
    }

    private var quickActions: some View {
        HStack {
            Button {
                showForm = true
            } label: {
                Label("Trocar conta", systemImage: "arrow.triangle.2.circlepath")
                    .font(TypeScale.cta)
                    .foregroundStyle(Palette.ivory)
                    .frame(maxWidth: .infinity)
            }
            Button {
                app.openPixAfterLogin = true
                Task { await app.loginDemo(preferredDemo) }
            } label: {
                Label("Fazer Pix", systemImage: "arrow.left.arrow.right")
                    .font(TypeScale.cta)
                    .foregroundStyle(Palette.gold)
                    .frame(maxWidth: .infinity)
            }
            .disabled(app.isBusy)
        }
        .padding(.vertical, 4)
    }

    private var demoAccounts: some View {
        CarbonCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Contas de demonstração")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                HStack(spacing: 10) {
                    demoChip(APIConfig.joao, "JP")
                    demoChip(APIConfig.maria, "MS")
                }
            }
        }
    }

    private func demoChip(_ demo: APIConfig.DemoAccount, _ initials: String) -> some View {
        Button {
            taxId = demo.taxId
            password = demo.password
            mode = .login
            Task { await app.loginDemo(demo) }
        } label: {
            HStack(spacing: 10) {
                InitialsAvatar(initials: initials, size: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text(demo.name)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(Palette.ivory)
                    Text(TaxID.formatted(demo.taxId))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(Palette.mute)
                        .lineLimit(1)
                        .minimumScaleFactor(0.75)
                }
                Spacer(minLength: 0)
            }
            .padding(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Palette.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .disabled(app.isBusy)
    }

    private var promo: some View {
        CarbonCard {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Pix real entre João e Maria")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Palette.ivory)
                    Text("O avaliador entra, transfere R$ 1,00 e vê o comprovante no ledger interno.")
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)
                }
                Spacer()
                Text("Simular")
                    .font(TypeScale.cta)
                    .foregroundStyle(Palette.ink)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Palette.gold)
                    .clipShape(Capsule())
                    .onTapGesture {
                        app.openPixAfterLogin = true
                        Task { await app.loginDemo(preferredDemo) }
                    }
            }
        }
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

    private var preferredDemo: APIConfig.DemoAccount {
        if LastAccountStore.taxId == APIConfig.maria.taxId { return APIConfig.maria }
        return APIConfig.joao
    }

    private func initials(_ name: String) -> String {
        String(name.split(separator: " ").prefix(2).compactMap(\.first)).uppercased()
    }

    private var canLogin: Bool {
        TaxID.digits(taxId).count >= 11 && password.count >= 8
    }

    private var canRegister: Bool {
        canLogin && fullName.trimmingCharacters(in: .whitespaces).count >= 3 && email.contains("@")
    }
}
