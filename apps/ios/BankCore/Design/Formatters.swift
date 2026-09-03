import Foundation

enum Money {
    private static let currency: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "BRL"
        formatter.locale = Locale(identifier: "pt_BR")
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        return formatter
    }()

    static func reais(_ value: Double) -> String {
        currency.string(from: NSNumber(value: value)) ?? "R$ 0,00"
    }

    static func signed(_ value: Double, credit: Bool) -> String {
        (credit ? "+ " : "− ") + reais(value)
    }

    static func parse(_ raw: String) -> Double? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.contains(",") {
            let normalized = trimmed
                .replacingOccurrences(of: ".", with: "")
                .replacingOccurrences(of: ",", with: ".")
            return Double(normalized)
        }
        return Double(trimmed)
    }
}

enum TaxID {
    static func digits(_ raw: String) -> String {
        raw.filter(\.isNumber)
    }

    static func formatted(_ raw: String) -> String {
        let d = digits(raw)
        guard d.count == 11 else { return d }
        let p1 = d.prefix(3)
        let p2 = d.dropFirst(3).prefix(3)
        let p3 = d.dropFirst(6).prefix(3)
        let p4 = d.suffix(2)
        return "\(p1).\(p2).\(p3)-\(p4)"
    }
}

enum BankDate {
    static let saoPaulo = TimeZone(identifier: "America/Sao_Paulo") ?? .current

    static func parseAPI(_ raw: String) -> Date? {
        var value = raw
        let hasZone = value.hasSuffix("Z")
            || value.contains("+")
            || (value.split(separator: "T").last?.contains("-") == true)
        if !hasZone {
            value += "Z"
        }
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = withFraction.date(from: value) { return date }
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        if let date = plain.date(from: value) { return date }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        for format in [
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXXXX",
            "yyyy-MM-dd'T'HH:mm:ss.SSSXXXXX",
            "yyyy-MM-dd'T'HH:mm:ssXXXXX",
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'",
            "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
            "yyyy-MM-dd'T'HH:mm:ss'Z'",
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
            "yyyy-MM-dd'T'HH:mm:ss",
        ] {
            formatter.dateFormat = format
            if let date = formatter.date(from: value) ?? formatter.date(from: raw) {
                return date
            }
        }
        return nil
    }

    static func display(_ date: Date, withTime: Bool = true) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "pt_BR")
        formatter.timeZone = saoPaulo
        formatter.dateFormat = withTime ? "dd/MM/yyyy HH:mm" : "dd/MM/yyyy"
        return formatter.string(from: date)
    }

    static func short(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "pt_BR")
        formatter.timeZone = saoPaulo
        formatter.dateFormat = "dd/MM HH:mm"
        return formatter.string(from: date)
    }
}
