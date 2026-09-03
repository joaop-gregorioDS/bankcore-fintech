import SwiftUI
import UIKit

struct HomeView: View {
    @Environment(AppState.self) private var app

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    greeting
                    balanceCard
                    GoldButton(title: "Pix", systemImage: "arrow.left.arrow.right") {
                        app.selectedTab = .pix
                    }
                    pixKeyCard
                    recent
                }
                .padding(16)
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { toolbar }
            .refreshable { await app.refresh() }
        }
    }

    @ToolbarContentBuilder
    private var toolbar: some ToolbarContent {
        ToolbarItem(placement: .principal) {
            Wordmark(size: 16)
        }
        ToolbarItem(placement: .topBarTrailing) {
            HStack(spacing: 14) {
                Button {
                    app.isBalanceHidden.toggle()
                } label: {
                    Image(systemName: app.isBalanceHidden ? "eye.slash" : "eye")
                        .foregroundStyle(Palette.mute)
                }
                Button("Sair") { app.logout() }
                    .foregroundStyle(Palette.debit)
                    .font(TypeScale.cta)
            }
        }
    }

    private var greeting: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(hello)
                .font(TypeScale.title)
                .foregroundStyle(Palette.ivory)
            HStack(spacing: 8) {
                Text("Conta \(app.account?.accountNumber ?? "—")")
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(Palette.mute)
                if app.account?.isActive == true {
                    StatusBadge(text: "Ativa")
                }
            }
        }
    }

    private var hello: String {
        let name = app.session?.fullName.split(separator: " ").first.map(String.init) ?? "correntista"
        return "Olá, \(name)"
    }

    private var balanceCard: some View {
        CarbonCard(padding: 20) {
            VStack(alignment: .leading, spacing: 10) {
                Text("Saldo em conta corrente")
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.mute)
                Text(app.isBalanceHidden ? "••••••" : Money.reais(app.account?.balanceReais ?? 0))
                    .font(TypeScale.balance)
                    .foregroundStyle(Palette.ivory)
                HStack {
                    Text("Limite Pix diurno")
                        .font(TypeScale.micro)
                        .foregroundStyle(Palette.mute)
                    Spacer()
                    Text(Money.reais(APIConfig.mockPixLimitReais))
                        .font(.system(size: 12, weight: .medium).monospacedDigit())
                        .foregroundStyle(Palette.mute)
                }
                .padding(.top, 6)
            }
        }
    }

    private var pixKeyCard: some View {
        CarbonCard {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Chave Pix (CPF)")
                        .font(TypeScale.micro)
                        .foregroundStyle(Palette.mute)
                    Text(TaxID.formatted(app.session?.taxId ?? ""))
                        .font(.system(size: 16, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Palette.gold)
                }
                Spacer()
                Button {
                    UIPasteboard.general.string = TaxID.digits(app.session?.taxId ?? "")
                } label: {
                    Image(systemName: "doc.on.doc")
                        .foregroundStyle(Palette.gold)
                        .padding(8)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var recent: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Últimos lançamentos")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(Palette.ivory)
                Spacer()
                Button("Ver extrato →") { app.selectedTab = .statement }
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.gold)
            }
            CarbonCard(padding: 8) {
                if app.statement.isEmpty {
                    Text("Nenhum lançamento ainda.")
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)
                        .padding(12)
                } else {
                    ForEach(Array(app.statement.prefix(4))) { tx in
                        Button { app.openReceipt(tx) } label: {
                            TransactionRow(transaction: tx)
                        }
                        .buttonStyle(.plain)
                        if tx.id != app.statement.prefix(4).last?.id {
                            Divider().background(Palette.line)
                        }
                    }
                }
            }
        }
    }
}
