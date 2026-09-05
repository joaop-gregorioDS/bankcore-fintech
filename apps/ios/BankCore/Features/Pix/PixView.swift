import SwiftUI
import UIKit

struct PixView: View {
    @Environment(AppState.self) private var app
    @State private var destination = ""
    @State private var amountText = ""
    @State private var descriptionText = "Pix BankCore"
    @State private var lookup: DirectoryEntry?
    @State private var confirming = false
    @State private var localError: String?
    @State private var sending = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    pixActions
                    form
                    if confirming, let lookup {
                        confirmation(lookup)
                    }
                    if let localError {
                        Text(localError)
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.debit)
                    }
                }
                .padding(16)
            }
            .background(Palette.ink.ignoresSafeArea())
            .navigationTitle("Pix")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Pix interno entre correntistas BankCore.")
                .font(TypeScale.body)
                .foregroundStyle(Palette.ivory)
            Text("A chave é o CPF só com dígitos. Não é SPI/DICT.")
                .font(TypeScale.label)
                .foregroundStyle(Palette.mute)
            Text("Saldo \(app.isBalanceHidden ? "••••••" : Money.reais(app.account?.balanceReais ?? 0))")
                .font(.system(size: 13, weight: .medium).monospacedDigit())
                .foregroundStyle(Palette.gold)
                .padding(.top, 4)
        }
    }

    private var pixActions: some View {
        HStack(spacing: 10) {
            pixChip("Minha chave", "person.text.rectangle") {
                UIPasteboard.general.string = TaxID.digits(app.session?.taxId ?? "")
                app.flash("Chave Pix (CPF) copiada.")
            }
            pixChip("QR Code", "qrcode") {
                app.simulate("Leitor de QR é simulação de UX. Use o CPF da Maria: 12345678900.")
            }
            pixChip("Limites", "slider.horizontal.3") {
                app.simulate("Limite Pix diurno \(Money.reais(app.mock.pixLimit)) · simulado.")
            }
        }
    }

    private func pixChip(_ title: String, _ icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                Image(systemName: icon)
                    .foregroundStyle(Palette.gold)
                Text(title)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(Palette.ivory)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Palette.card)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Palette.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private var form: some View {
        CarbonCard(padding: 18) {
            VStack(spacing: 14) {
                CarbonField(
                    label: "Chave Pix de destino (CPF)",
                    text: $destination,
                    placeholder: "12345678900",
                    keyboard: .numberPad,
                    mono: true
                )
                CarbonField(
                    label: "Valor",
                    text: $amountText,
                    placeholder: "1,00",
                    keyboard: .decimalPad,
                    mono: true
                )
                CarbonField(
                    label: "Descrição",
                    text: $descriptionText,
                    placeholder: "Pix BankCore"
                )
                GoldButton(
                    title: confirming ? "Atualizar destinatário" : "Continuar",
                    isLoading: sending,
                    enabled: canContinue
                ) {
                    Task { await lookupDestination() }
                }
            }
        }
    }

    private func confirmation(_ entry: DirectoryEntry) -> some View {
        CarbonCard(padding: 18) {
            VStack(alignment: .leading, spacing: 12) {
                Text("Confirmar Pix")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Palette.ivory)
                row("Destinatário", entry.fullName)
                row("CPF", TaxID.formatted(entry.taxId))
                HStack {
                    Text("Valor")
                        .font(TypeScale.label)
                        .foregroundStyle(Palette.mute)
                    Spacer()
                    Text(Money.reais(parsedAmount ?? 0))
                        .font(TypeScale.amount)
                        .foregroundStyle(Palette.ivory)
                }
                if !descriptionText.trimmingCharacters(in: .whitespaces).isEmpty {
                    row("Descrição", descriptionText)
                }
                GoldButton(title: "Confirmar Pix", systemImage: "checkmark", isLoading: sending) {
                    Task { await send() }
                }
            }
        }
    }

    private func row(_ label: String, _ value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(TypeScale.label)
                .foregroundStyle(Palette.mute)
            Spacer()
            Text(value)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Palette.ivory)
                .multilineTextAlignment(.trailing)
        }
    }

    private var parsedAmount: Double? {
        Money.parse(amountText)
    }

    private var canContinue: Bool {
        TaxID.digits(destination).count >= 11 && (parsedAmount ?? 0) > 0
    }

    private func lookupDestination() async {
        localError = nil
        confirming = false
        sending = true
        defer { sending = false }
        do {
            lookup = try await app.lookupPix(taxId: destination)
            confirming = true
        } catch {
            lookup = nil
            localError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func send() async {
        guard let amount = parsedAmount, amount > 0 else { return }
        localError = nil
        sending = true
        defer { sending = false }
        do {
            _ = try await app.sendPix(
                destinationKey: destination,
                amountReais: amount,
                description: descriptionText.trimmingCharacters(in: .whitespacesAndNewlines)
            )
            destination = ""
            amountText = ""
            descriptionText = "Pix BankCore"
            lookup = nil
            confirming = false
        } catch {
            localError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}
