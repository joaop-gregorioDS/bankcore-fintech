import SwiftUI
import UIKit

struct Wordmark: View {
    var size: CGFloat = 32

    var body: some View {
        HStack(spacing: 0) {
            Text("Bank")
                .foregroundStyle(Palette.ivory)
            Text("Core")
                .foregroundStyle(Palette.gold)
        }
        .font(.system(size: size, weight: .semibold))
        .tracking(-0.4)
    }
}

struct CarbonCard<Content: View>: View {
    var padding: CGFloat = 16
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Palette.card)
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Palette.line, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct GoldButton: View {
    let title: String
    var systemImage: String? = nil
    var isLoading: Bool = false
    var enabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .tint(Palette.ink)
                } else if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title.uppercased())
                    .font(TypeScale.cta)
                    .tracking(0.8)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .foregroundStyle(Palette.ink)
            .background(enabled && !isLoading ? Palette.gold : Palette.gold.opacity(0.35))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(!enabled || isLoading)
    }
}

struct SecondaryButton: View {
    let title: String
    var systemImage: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
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
        .buttonStyle(.plain)
    }
}

struct FieldLabel: View {
    let text: String
    var body: some View {
        Text(text)
            .font(TypeScale.label)
            .foregroundStyle(Palette.mute)
    }
}

struct CarbonField: View {
    let label: String
    @Binding var text: String
    var placeholder: String = ""
    var keyboard: UIKeyboardType = .default
    var isSecure: Bool = false
    var mono: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            FieldLabel(text: label)
            Group {
                if isSecure {
                    SecureField(placeholder, text: $text)
                } else {
                    TextField(placeholder, text: $text)
                        .keyboardType(keyboard)
                }
            }
            .font(mono ? .system(size: 15, design: .monospaced) : TypeScale.body)
            .foregroundStyle(Palette.ivory)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(Palette.input)
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(Palette.line, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }
}

struct DemoBanner: View {
    var body: some View {
        Text("Ambiente de portfólio — login, Pix, extrato e comprovante no ledger interno")
            .font(TypeScale.micro)
            .foregroundStyle(Palette.gold)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
    }
}

struct AmountText: View {
    let value: Double
    var credit: Bool? = nil
    var size: Font = TypeScale.amount

    var body: some View {
        Text(label)
            .font(size)
            .foregroundStyle(color)
            .monospacedDigit()
    }

    private var label: String {
        if let credit {
            return Money.signed(value, credit: credit)
        }
        return Money.reais(value)
    }

    private var color: Color {
        if credit == false { return Palette.debit }
        return Palette.ivory
    }
}

struct TransactionRow: View {
    let transaction: LedgerTransaction

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(transaction.isCredit ? Palette.gold.opacity(0.12) : Palette.debit.opacity(0.12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(transaction.isCredit ? Palette.gold.opacity(0.28) : Palette.debit.opacity(0.28), lineWidth: 1)
                    )
                Image(systemName: transaction.isCredit ? "arrow.down.left" : "arrow.up.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(transaction.isCredit ? Palette.gold : Palette.debit)
            }
            .frame(width: 36, height: 36)

            VStack(alignment: .leading, spacing: 3) {
                Text(transaction.title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Palette.ivory)
                    .lineLimit(1)
                Text("\(BankDate.short(transaction.createdAt)) · \(transaction.idempotencyKey.prefix(12))…")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(Palette.mute)
            }

            Spacer(minLength: 8)

            AmountText(value: transaction.amountReais, credit: transaction.isCredit)
        }
        .padding(.vertical, 10)
    }
}

struct StatusBadge: View {
    let text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 10, weight: .semibold))
            .tracking(0.6)
            .foregroundStyle(Palette.status)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .overlay(
                Capsule()
                    .stroke(Palette.status.opacity(0.35), lineWidth: 1)
            )
            .background(Palette.status.opacity(0.12), in: Capsule())
    }
}
