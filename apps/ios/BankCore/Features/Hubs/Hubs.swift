import SwiftUI

struct HubSheet: View {
    @Environment(AppState.self) private var app
    let hub: AppState.Hub

    var body: some View {
        NavigationStack {
            Group {
                switch hub {
                case .pay: PayHubView()
                case .dda: DDAHubView()
                case .invest: InvestHubView()
                case .credit: CreditHubView()
                case .more: MoreHubView()
                case .notifications: NotificationsView()
                case .invoice: InvoiceHubView()
                }
            }
            .background(Palette.ink.ignoresSafeArea())
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Fechar") { app.presentedHub = nil }
                        .foregroundStyle(Palette.gold)
                }
            }
        }
        .presentationDetents(hub == .notifications || hub == .more ? [.medium, .large] : [.large])
        .preferredColorScheme(.dark)
    }
}

struct PayHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header("Pagar", "Boletos, tributos e DDA são simulação de UX. Só Pix e depósito gravam no ledger.")
                tile("Pix", "arrow.left.arrow.right", "Ledger real · CPF de outro correntista.") {
                    app.presentedHub = nil
                    app.selectedTab = .pix
                }
                tile("Boleto", "barcode", "Linha digitável ilustrativa.") {
                    app.simulate("Simulação: boleto não altera o ledger.")
                }
                tile("Agenda DDA", "calendar", "\(app.mock.dda.count) títulos · \(Money.reais(app.mock.scheduledTotal))") {
                    app.presentedHub = .dda
                }
                tile("Débito automático", "arrow.triangle.2.circlepath", "Gestão ilustrativa.") {
                    app.simulate("Débito automático é UX simulada.")
                }
            }
            .padding(16)
        }
        .navigationTitle("Pagar")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func header(_ title: String, _ subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack { SectionTitle(text: title); SimulatedBadge() }
            Text(subtitle).font(TypeScale.label).foregroundStyle(Palette.mute)
        }
    }

    private func tile(_ title: String, _ icon: String, _ subtitle: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            CarbonCard {
                HStack(spacing: 12) {
                    Image(systemName: icon)
                        .foregroundStyle(Palette.gold)
                        .frame(width: 36, height: 36)
                        .background(Palette.gold.opacity(0.12))
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    VStack(alignment: .leading, spacing: 3) {
                        Text(title).font(.system(size: 15, weight: .semibold)).foregroundStyle(Palette.ivory)
                        Text(subtitle).font(TypeScale.label).foregroundStyle(Palette.mute)
                    }
                    Spacer()
                    Image(systemName: "chevron.right").foregroundStyle(Palette.mute).font(.caption)
                }
            }
        }
        .buttonStyle(.plain)
    }
}

struct DDAHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        List {
            Section {
                HStack {
                    Text("Total agendado")
                    Spacer()
                    Text(Money.reais(app.mock.scheduledTotal))
                        .font(TypeScale.amount)
                        .foregroundStyle(Palette.debit)
                }
                .listRowBackground(Palette.card)
            }
            Section {
                ForEach(app.mock.dda) { bill in
                    Button {
                        app.simulate("Simulação: \(bill.payee) · \(Money.reais(bill.amount)) não liquida no ledger.")
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(bill.payee)
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundStyle(Palette.ivory)
                                Text("Vence \(bill.due)")
                                    .font(TypeScale.micro)
                                    .foregroundStyle(Palette.mute)
                            }
                            Spacer()
                            Text(Money.reais(bill.amount))
                                .font(TypeScale.amount)
                                .foregroundStyle(Palette.ivory)
                        }
                    }
                    .listRowBackground(Palette.card)
                }
            } header: {
                HStack {
                    Text("Boletos eletrônicos")
                    SimulatedBadge()
                }
            }
        }
        .scrollContentBackground(.hidden)
        .navigationTitle("Agenda DDA")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct InvestHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack { SectionTitle(text: "BankCore Invest"); SimulatedBadge() }
                Text("Posição ilustrativa. CDB e Tesouro não liquidam no ledger.")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                CarbonCard {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Patrimônio")
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                        Text(Money.reais(app.mock.investTotal))
                            .font(.system(size: 32, weight: .semibold).monospacedDigit())
                            .foregroundStyle(Palette.ivory)
                    }
                }
                ForEach(app.mock.investments) { item in
                    CarbonCard {
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(item.name)
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundStyle(Palette.ivory)
                                Text(item.yield)
                                    .font(TypeScale.micro)
                                    .foregroundStyle(Palette.status)
                            }
                            Spacer()
                            Text(Money.reais(item.amount))
                                .font(TypeScale.amount)
                                .foregroundStyle(Palette.ivory)
                        }
                    }
                }
                GoldButton(title: "Simular aplicação") {
                    app.simulate("Simulação: aplicação de R$ 100/mês. Não grava no ledger.")
                }
            }
            .padding(16)
        }
        .navigationTitle("Investir")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct CreditHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack { SectionTitle(text: "Crédito"); SimulatedBadge() }
                Text("Tabela Price ilustrativa. Empréstimo não liquida no ledger.")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                CarbonCard {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Limite pré-aprovado")
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                        Text(Money.reais(app.mock.creditLimit))
                            .font(.system(size: 32, weight: .semibold).monospacedDigit())
                            .foregroundStyle(Palette.ivory)
                        Text("Segmento \(app.mock.segment)")
                            .font(TypeScale.micro)
                            .foregroundStyle(Palette.gold)
                    }
                }
                CarbonCard {
                    VStack(alignment: .leading, spacing: 10) {
                        row("Valor ilustrativo", Money.reais(10_000))
                        row("Prazo", "24 meses")
                        row("CET a.m.", "1,79%")
                        row("Parcela", Money.reais(512.40))
                    }
                }
                GoldButton(title: "Simular contratação") {
                    app.simulate("Simulação: crédito Tabela Price. Não grava no ledger.")
                }
            }
            .padding(16)
        }
        .navigationTitle("Empréstimo")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func row(_ k: String, _ v: String) -> some View {
        HStack {
            Text(k).font(TypeScale.label).foregroundStyle(Palette.mute)
            Spacer()
            Text(v).font(.system(size: 14, weight: .semibold)).foregroundStyle(Palette.ivory)
        }
    }
}

struct MoreHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        List {
            Section {
                Button {
                    app.presentedHub = nil
                    app.selectedTab = .pix
                } label: {
                    Label("Pix (ledger real)", systemImage: "arrow.left.arrow.right")
                }
                .listRowBackground(Palette.card)
                Button {
                    app.presentedHub = nil
                    app.selectedTab = .statement
                } label: {
                    Label("Extrato (ledger real)", systemImage: "list.bullet.rectangle")
                }
                .listRowBackground(Palette.card)
            }
            Section("Simulado") {
                Button("Cartões") { app.presentedHub = nil; app.selectedTab = .cards }
                    .listRowBackground(Palette.card)
                Button("Agenda DDA") { app.presentedHub = .dda }
                    .listRowBackground(Palette.card)
                Button("BankCore Invest") { app.presentedHub = .invest }
                    .listRowBackground(Palette.card)
                Button("Crédito") { app.presentedHub = .credit }
                    .listRowBackground(Palette.card)
                Button("Cobranças PJ") { app.simulate("Cobranças PJ são UX simulada.") }
                    .listRowBackground(Palette.card)
            }
        }
        .scrollContentBackground(.hidden)
        .navigationTitle("Ver mais")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct NotificationsView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        List {
            ForEach(app.mock.notifications) { item in
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: item.icon)
                        .foregroundStyle(Palette.gold)
                        .frame(width: 28)
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(item.title)
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Palette.ivory)
                            if item.simulated { SimulatedBadge() }
                        }
                        Text(item.body)
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                        Text(item.time)
                            .font(TypeScale.micro)
                            .foregroundStyle(Palette.mute)
                    }
                }
                .listRowBackground(Palette.card)
                .padding(.vertical, 4)
            }
        }
        .scrollContentBackground(.hidden)
        .navigationTitle("Notificações")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct InvoiceHubView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        let card = app.mock.primaryCard
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack { SectionTitle(text: "Fatura"); SimulatedBadge() }
                CarbonCard {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(card.name).font(TypeScale.label).foregroundStyle(Palette.mute)
                        Text(Money.reais(card.invoice))
                            .font(.system(size: 32, weight: .semibold).monospacedDigit())
                            .foregroundStyle(Palette.ivory)
                        Text("Vencimento \(card.dueLabel) · \(card.period)")
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                    }
                }
                Text("Módulo didático. Esta fatura não liquida no ledger BankCore.")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                GoldButton(title: "Pagar fatura (simulado)") {
                    app.simulate("Simulação: pagamento de fatura. Não altera o saldo do ledger.")
                }
            }
            .padding(16)
        }
        .navigationTitle("Fatura")
        .navigationBarTitleDisplayMode(.inline)
    }
}
