import SwiftUI

struct ReceiptView: View {
    @Environment(AppState.self) private var app
    @Environment(\.dismiss) private var dismiss
    let transaction: LedgerTransaction
    @State private var pdfURL: URL?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    paper
                        .padding(16)
                    actions
                        .padding(.horizontal, 16)
                        .padding(.bottom, 24)
                }
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationTitle("Comprovante")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Fechar") { dismiss() }
                        .foregroundStyle(Palette.gold)
                }
            }
            .onAppear { preparePDF() }
        }
        .presentationDetents([.large])
        .preferredColorScheme(.dark)
    }

    private var holder: String { app.session?.fullName ?? "Correntista BankCore" }
    private var taxId: String { app.session?.taxId ?? "" }
    private var accountNumber: String { app.account?.accountNumber ?? "—" }

    private var paper: some View {
        VStack(alignment: .leading, spacing: 0) {
            Rectangle()
                .fill(Palette.paperGold)
                .frame(height: 3)
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 0) {
                            Text("Bank").foregroundStyle(Palette.paperInk)
                            Text("Core").foregroundStyle(Palette.paperGold)
                        }
                        .font(.system(size: 18, weight: .semibold))
                        Text("Comprovante · ledger interno")
                            .font(TypeScale.micro)
                            .foregroundStyle(Palette.paperMute)
                    }
                    Spacer()
                    Text("LIQUIDADO")
                        .font(.system(size: 10, weight: .semibold))
                        .tracking(0.5)
                        .foregroundStyle(Palette.paperGold)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(Palette.paperGold.opacity(0.45), lineWidth: 1)
                        )
                }

                VStack(spacing: 6) {
                    Text("Valor da operação")
                        .font(TypeScale.micro)
                        .foregroundStyle(Palette.paperMute)
                    Text(Money.signed(transaction.amountReais, credit: transaction.isCredit))
                        .font(.system(size: 32, weight: .semibold).monospacedDigit())
                        .foregroundStyle(transaction.isCredit ? Palette.paperInk : Palette.paperDebit)
                    Text(holder)
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.paperMute)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)

                VStack(spacing: 10) {
                    paperRow("Tipo", transaction.typeLabel)
                    paperRow("Descrição", transaction.description ?? transaction.title)
                    paperRow("Data/Hora", BankDate.display(transaction.createdAt))
                    paperRow("Autenticação", "AUT-\(transaction.idempotencyKey.uppercased())", gold: true)
                    paperRow("Conta", accountNumber)
                }
                .padding(.vertical, 12)
                .overlay(alignment: .top) { Rectangle().fill(Palette.paperLine).frame(height: 1) }
                .overlay(alignment: .bottom) { Rectangle().fill(Palette.paperLine).frame(height: 1) }

                Text("Vortex Software · documento de demonstração. Não é comprovante SPI/BACEN. A liquidação ocorreu no livro-razão BankCore (partidas dobradas).")
                    .font(.system(size: 10))
                    .foregroundStyle(Palette.paperMute)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(20)
        }
        .background(Palette.paper)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func paperRow(_ label: String, _ value: String, gold: Bool = false) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(TypeScale.label)
                .foregroundStyle(Palette.paperMute)
            Spacer()
            Text(value)
                .font(.system(size: 12, weight: .semibold, design: gold ? .monospaced : .default))
                .foregroundStyle(gold ? Palette.paperGold : Palette.paperInk)
                .multilineTextAlignment(.trailing)
        }
    }

    private var actions: some View {
        VStack(spacing: 10) {
            if let pdfURL {
                ShareLink(
                    item: pdfURL,
                    subject: Text("Comprovante BankCore"),
                    message: Text(shareText),
                    preview: SharePreview("Comprovante BankCore · ledger interno", icon: Image(systemName: "doc.richtext"))
                ) {
                    HStack {
                        Image(systemName: "square.and.arrow.up")
                        Text("COMPARTILHAR")
                            .font(TypeScale.cta)
                            .tracking(0.8)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .foregroundStyle(Palette.ink)
                    .background(Palette.gold)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
            ShareLink(item: shareText) {
                HStack {
                    Image(systemName: "doc.plaintext")
                    Text("Compartilhar texto")
                        .font(TypeScale.cta)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 13)
                .foregroundStyle(Palette.ivory)
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Palette.line, lineWidth: 1)
                )
            }
        }
    }

    private var shareText: String {
        ReceiptDocument.shareText(
            transaction: transaction,
            holder: holder,
            taxId: taxId,
            accountNumber: accountNumber
        )
    }

    private func preparePDF() {
        pdfURL = try? ReceiptDocument.pdfURL(
            transaction: transaction,
            holder: holder,
            taxId: taxId,
            accountNumber: accountNumber
        )
    }
}
