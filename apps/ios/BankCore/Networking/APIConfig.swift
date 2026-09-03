import Foundation

enum APIConfig {
    /// Demo VPS is HTTP. Info.plist ATS exception is for this IP; NSAllowsArbitraryLoads
    /// is lab-only because ATS exception domains do not apply to raw IP addresses.
    static let host = "2.25.126.53"
    static let baseURL = URL(string: "http://2.25.126.53")!

    static let joao = DemoAccount(
        name: "João Paulo",
        taxId: "33548376835",
        password: "teste123456"
    )
    static let maria = DemoAccount(
        name: "Maria Silva",
        taxId: "12345678900",
        password: "teste123456"
    )

    /// Mock UX only — not a ledger field.
    static let mockPixLimitReais: Double = 20_000

    struct DemoAccount {
        let name: String
        let taxId: String
        let password: String
    }

    static func url(_ path: String) -> URL {
        var base = baseURL.absoluteString
        if base.hasSuffix("/") { base.removeLast() }
        let suffix = path.hasPrefix("/") ? path : "/" + path
        guard let url = URL(string: base + suffix) else {
            preconditionFailure("Invalid API path: \(path)")
        }
        return url
    }
}
