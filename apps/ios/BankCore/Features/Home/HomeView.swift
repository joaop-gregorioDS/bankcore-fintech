import SwiftUI
import UIKit

struct HomeView: View {
    @Environment(AppState.self) private var app

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 4)

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        balanceRow
                        shortcutGrid
                        promo
                        cardsPreview
                        pixKeyCard
                        recent
                    }
                    .padding(16)
                    .padding(.bottom, 24)
                }
                .refreshable { await app.refresh() }
            }
            .background(Palette.ink.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            BrandMark(size: 28)
            Text("Olá, \(app.mock.firstName)")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(Palette.ivory)
            Spacer()
            Button {
                app.isBalanceHidden.toggle()
            } label: {
                Image(systemName: app.isBalanceHidden ? "eye.slash" : "eye")
                    .foregroundStyle(Palette.ivory)
                    .frame(width: 32, height: 32)
            }
            Button {
                app.presentedHub = .notifications
            } label: {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: "bell")
                        .foregroundStyle(Palette.ivory)
                        .frame(width: 32, height: 32)
                    Text("\(app.mock.notifications.count)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(Palette.ink)
                        .padding(.horizontal, 4)
                        .padding(.vertical, 1)
                        .background(Palette.gold)
                        .clipShape(Capsule())
                        .offset(x: 6, y: -4)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Palette.panel)
        .overlay(alignment: .bottom) { Rectangle().fill(Palette.line).frame(height: 1) }
    }

    private var balanceRow: some View {
        CarbonCard(padding: 16) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Saldo")
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)
                    Text(hidden(app.account?.balanceReais ?? 0))
                        .font(.system(size: 28, weight: .semibold).monospacedDigit())
                        .foregroundStyle(Palette.ivory)
                    HStack(spacing: 6) {
                        Text("Cc. \(app.account?.accountNumber ?? "—")")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(Palette.mute)
                        if app.account?.isActive == true {
                            StatusBadge(text: "Ativa")
                        }
                    }
                    .padding(.top, 4)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    HStack(spacing: 6) {
                        Text("Agendado")
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                        SimulatedBadge()
                    }
                    Text(app.isBalanceHidden ? "••••••" : Money.signed(app.mock.scheduledTotal, credit: false))
                        .font(.system(size: 20, weight: .semibold).monospacedDigit())
                        .foregroundStyle(Palette.debit)
                    Button("Ver DDA") { app.presentedHub = .dda }
                        .font(TypeScale.micro)
                        .foregroundStyle(Palette.gold)
                        .padding(.top, 2)
                }
            }
        }
    }

    private var shortcutGrid: some View {
        LazyVGrid(columns: columns, spacing: 12) {
            ShortcutButton(title: "Extrato", systemImage: "list.bullet.rectangle") {
                app.selectedTab = .statement
            }
            ShortcutButton(title: "Pagar", systemImage: "barcode") {
                app.presentedHub = .pay
            }
            ShortcutButton(title: "Pix", systemImage: "arrow.left.arrow.right") {
                app.selectedTab = .pix
            }
            ShortcutButton(title: "Investir", systemImage: "chart.line.uptrend.xyaxis") {
                app.presentedHub = .invest
            }
            ShortcutButton(title: "Cartões", systemImage: "creditcard") {
                app.selectedTab = .cards
            }
            ShortcutButton(title: "Empréstimo", systemImage: "banknote") {
                app.presentedHub = .credit
            }
            ShortcutButton(title: "DDA", systemImage: "calendar") {
                app.presentedHub = .dda
            }
            ShortcutButton(title: "Ver mais", systemImage: "ellipsis") {
                app.presentedHub = .more
            }
        }
    }

    private var promo: some View {
        CarbonCard {
            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Text(app.mock.promoTitle)
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(Palette.ivory)
                        SimulatedBadge()
                    }
                    Text(app.mock.promoBody)
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)
                }
                Spacer(minLength: 8)
                Button("Simular") {
                    app.presentedHub = .invest
                }
                .font(TypeScale.cta)
                .foregroundStyle(Palette.ink)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(Palette.gold)
                .clipShape(Capsule())
            }
        }
    }

    private var cardsPreview: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                SectionTitle(text: "Cartões")
                SimulatedBadge()
                Spacer()
                Button("Ver todos") { app.selectedTab = .cards }
                    .font(TypeScale.label)
                    .foregroundStyle(Palette.gold)
            }
            let card = app.mock.primaryCard
            CarbonCard {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(hidden(card.used))
                                .font(TypeScale.amount)
                                .foregroundStyle(Palette.ivory)
                            Text("Limite utilizado")
                                .font(TypeScale.micro)
                                .foregroundStyle(Palette.mute)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 2) {
                            Text(hidden(card.available))
                                .font(TypeScale.amount)
                                .foregroundStyle(Palette.ivory)
                            Text("Disponível")
                                .font(TypeScale.micro)
                                .foregroundStyle(Palette.mute)
                        }
                    }
                    LimitBar(ratio: card.usedRatio)
                }
            }
            TabView {
                ForEach(app.mock.cards) { item in
                    Button { app.selectedTab = .cards } label: {
                        PlasticCard(card: item)
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 2)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .automatic))
            .frame(height: 200)
            .tint(Palette.gold)
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
                    app.flash("Chave Pix copiada.")
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
                    Text("Nenhum lançamento no ledger ainda.")
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

    private func hidden(_ value: Double) -> String {
        app.isBalanceHidden ? "••••••" : Money.reais(value)
    }
}
