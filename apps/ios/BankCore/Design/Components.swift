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

struct BrandMark: View {
    var size: CGFloat = 48

    var body: some View {
        Image(systemName: "shield")
            .font(.system(size: size * 0.42, weight: .medium))
            .foregroundStyle(Palette.gold)
            .frame(width: size, height: size)
            .overlay(
                RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                    .stroke(Palette.gold, lineWidth: max(1.2, size * 0.035))
            )
    }
}

enum AppVersion {
    static var marketing: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.10.25"
    }

    static var line: String { "version \(marketing)" }
}

struct VersionLabel: View {
    var body: some View {
        Text(AppVersion.line)
            .font(.system(size: 11, weight: .medium, design: .monospaced))
            .foregroundStyle(Palette.mute)
            .tracking(0.6)
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

struct SimulatedBadge: View {
    var body: some View {
        Text("SIMULADO")
            .font(.system(size: 9, weight: .semibold))
            .tracking(0.6)
            .foregroundStyle(Palette.gold)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .overlay(
                Capsule().stroke(Palette.gold.opacity(0.45), lineWidth: 1)
            )
    }
}

struct InitialsAvatar: View {
    let initials: String
    var size: CGFloat = 44

    var body: some View {
        Text(initials)
            .font(.system(size: size * 0.36, weight: .semibold))
            .foregroundStyle(Palette.gold)
            .frame(width: size, height: size)
            .background(Palette.gold.opacity(0.12))
            .overlay(
                Circle().stroke(Palette.gold.opacity(0.55), lineWidth: 1)
            )
            .clipShape(Circle())
    }
}

struct ShortcutButton: View {
    let title: String
    let systemImage: String
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                ZStack {
                    Circle()
                        .fill(Palette.gold.opacity(0.12))
                    Image(systemName: systemImage)
                        .font(.system(size: 18, weight: .medium))
                        .foregroundStyle(Palette.gold)
                }
                .frame(width: 56, height: 56)
                Text(title)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(Palette.ivory)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .frame(height: 28, alignment: .top)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }
}

struct LimitBar: View {
    let ratio: Double

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(Palette.line)
                Capsule()
                    .fill(Palette.gold)
                    .frame(width: max(8, geo.size.width * ratio))
            }
        }
        .frame(height: 6)
    }
}

struct SectionTitle: View {
    let text: String
    var body: some View {
        Text(text)
            .font(.system(size: 20, weight: .semibold))
            .foregroundStyle(Palette.ivory)
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    var subtitle: String? = nil
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .medium))
                    .foregroundStyle(Palette.gold)
                    .frame(width: 28, alignment: .center)
                    .padding(.top, 2)
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Palette.ivory)
                    if let subtitle {
                        Text(subtitle)
                            .font(TypeScale.label)
                            .foregroundStyle(Palette.mute)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Palette.mute)
            }
            .padding(.vertical, 12)
        }
        .buttonStyle(.plain)
    }
}

struct PlasticCard: View {
    let card: MockCard

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                HStack(spacing: 0) {
                    Text("Bank").foregroundStyle(.white)
                    Text("Core").foregroundStyle(Palette.gold)
                }
                .font(.system(size: 13, weight: .semibold))
                Spacer()
                Text(card.name.uppercased())
                    .font(.system(size: 10, weight: .semibold))
                    .tracking(0.8)
                    .foregroundStyle(Palette.gold)
            }
            Text(Money.reais(card.invoice))
                .font(.system(size: 26, weight: .semibold).monospacedDigit())
                .foregroundStyle(.white)
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Vencimento").font(TypeScale.micro).foregroundStyle(Palette.mute)
                    Text(card.dueLabel).font(.system(size: 12, weight: .medium)).foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Compras").font(TypeScale.micro).foregroundStyle(Palette.mute)
                    Text(card.period).font(.system(size: 12, weight: .medium)).foregroundStyle(.white)
                }
            }
            HStack {
                Text("•••• \(card.last4)")
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(Palette.ivory.opacity(0.8))
                Spacer()
                Text(card.brand.uppercased())
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Palette.mute)
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, minHeight: 176, alignment: .leading)
        .background(gradient)
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Palette.gold.opacity(0.35), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var gradient: LinearGradient {
        switch card.theme {
        case .black:
            return LinearGradient(colors: [Color(hex: "#1A1A1C"), Color(hex: "#0D0D0E")], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .platinum:
            return LinearGradient(colors: [Color(hex: "#2A2A2E"), Color(hex: "#141416")], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .virtual:
            return LinearGradient(colors: [Color(hex: "#161618"), Color(hex: "#0B0B0C")], startPoint: .topLeading, endPoint: .bottomTrailing)
        }
    }
}
