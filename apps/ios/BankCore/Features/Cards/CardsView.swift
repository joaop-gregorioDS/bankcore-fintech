import SwiftUI

struct CardsView: View {
    @Environment(AppState.self) private var app
    @State private var page = 0

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        SectionTitle(text: "Cartões")
                        SimulatedBadge()
                    }
                    Text("Módulo didático. Fatura e limite não liquidam no ledger BankCore.")
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)

                    let card = current
                    CarbonCard {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(app.isBalanceHidden ? "••••••" : Money.reais(card.used))
                                        .font(.system(size: 22, weight: .semibold).monospacedDigit())
                                        .foregroundStyle(Palette.ivory)
                                    Text("Limite utilizado").font(TypeScale.micro).foregroundStyle(Palette.mute)
                                }
                                Spacer()
                                VStack(alignment: .trailing, spacing: 2) {
                                    Text(app.isBalanceHidden ? "••••••" : Money.reais(card.available))
                                        .font(.system(size: 22, weight: .semibold).monospacedDigit())
                                        .foregroundStyle(Palette.ivory)
                                    Text("Disponível").font(TypeScale.micro).foregroundStyle(Palette.mute)
                                }
                            }
                            LimitBar(ratio: card.usedRatio)
                            HStack {
                                Text("Total \(Money.reais(card.total))")
                                Spacer()
                                Text("Renovação 10/Set")
                            }
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(Palette.mute)
                        }
                    }

                    TabView(selection: $page) {
                        ForEach(Array(app.mock.cards.enumerated()), id: \.element.id) { index, item in
                            PlasticCard(card: item)
                                .padding(.horizontal, 4)
                                .tag(index)
                        }
                    }
                    .tabViewStyle(.page(indexDisplayMode: .automatic))
                    .frame(height: 210)
                    .tint(Palette.gold)

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        cardAction("Pagar fatura", "banknote") { app.presentedHub = .invoice }
                        cardAction("Carteira", "wallet.pass") { app.simulate("Simulação: Apple Wallet. Não grava no ledger.") }
                        cardAction("Virtual", "creditcard") { app.simulate("Cartão virtual gerado (UX). Não grava no ledger.") }
                        cardAction("Bloquear", "lock") { app.simulate("Simulação: cartão bloqueado/desbloqueado.") }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Últimos lançamentos")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(Palette.ivory)
                            Spacer()
                            Text("Fatura atual · Set")
                                .font(TypeScale.micro)
                                .foregroundStyle(Palette.mute)
                        }
                        CarbonCard(padding: 8) {
                            ForEach(app.mock.cardPurchases) { item in
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(item.merchant)
                                            .font(.system(size: 13, weight: .semibold))
                                            .foregroundStyle(Palette.ivory)
                                        Text(item.detail)
                                            .font(.system(size: 11))
                                            .foregroundStyle(Palette.mute)
                                    }
                                    Spacer()
                                    Text(Money.reais(item.amount))
                                        .font(TypeScale.amount)
                                        .foregroundStyle(Palette.debit)
                                }
                                .padding(.vertical, 8)
                                if item.id != app.mock.cardPurchases.last?.id {
                                    Divider().background(Palette.line)
                                }
                            }
                        }
                    }
                }
                .padding(16)
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) { Wordmark(size: 16) }
            }
        }
    }

    private var current: MockCard {
        let cards = app.mock.cards
        guard cards.indices.contains(page) else { return cards[0] }
        return cards[page]
    }

    private func cardAction(_ title: String, _ icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Palette.gold)
                    .frame(width: 40, height: 40)
                    .background(Palette.gold.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                Text(title)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(Palette.ivory)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }
}
