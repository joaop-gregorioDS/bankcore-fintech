import SwiftUI

struct StatementView: View {
    @Environment(AppState.self) private var app

    private var income: Double {
        app.statement.filter(\.isCredit).reduce(0) { $0 + $1.amountReais }
    }

    private var expense: Double {
        app.statement.filter { !$0.isCredit }.reduce(0) { $0 + $1.amountReais }
    }

    var body: some View {
        NavigationStack {
            Group {
                if app.statement.isEmpty {
                    ContentUnavailableView(
                        "Sem lançamentos",
                        systemImage: "list.bullet.rectangle",
                        description: Text("Pix e depósitos do ledger aparecem aqui.")
                    )
                    .foregroundStyle(Palette.mute)
                } else {
                    List {
                        Section {
                            summary
                                .listRowBackground(Palette.card)
                                .listRowSeparator(.hidden)
                        }
                        Section {
                            ForEach(app.statement) { tx in
                                Button { app.openReceipt(tx) } label: {
                                    TransactionRow(transaction: tx)
                                }
                                .listRowBackground(Palette.card)
                                .listRowSeparatorTint(Palette.line)
                            }
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationTitle("Extrato")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable { await app.refresh() }
        }
    }

    private var summary: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Entradas")
                    .font(TypeScale.micro)
                    .foregroundStyle(Palette.mute)
                Text(Money.signed(income, credit: true))
                    .font(TypeScale.amount)
                    .foregroundStyle(Palette.ivory)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text("Saídas")
                    .font(TypeScale.micro)
                    .foregroundStyle(Palette.mute)
                Text(Money.signed(expense, credit: false))
                    .font(TypeScale.amount)
                    .foregroundStyle(Palette.debit)
            }
        }
        .padding(.vertical, 6)
    }
}
