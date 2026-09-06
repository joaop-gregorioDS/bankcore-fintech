import Foundation

enum APIConfig {
    static let host = "bankcore.vortexsoftware.tech"
    static let baseURL = URL(string: "https://bankcore.vortexsoftware.tech")!

    static let lucas = DemoAccount(
        name: "Lucas Mendes",
        taxId: "98765432100",
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
