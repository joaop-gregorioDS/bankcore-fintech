import Foundation

enum JWT {
    struct Payload: Decodable {
        let sub: String
        let taxId: String?
        let name: String?
        let exp: TimeInterval?

        enum CodingKeys: String, CodingKey {
            case sub, name, exp
            case taxId = "tax_id"
        }

        var userId: UUID? { UUID(uuidString: sub) }

        var isExpired: Bool {
            guard let exp else { return false }
            return Date().timeIntervalSince1970 >= exp
        }
    }

    static func payload(from token: String) throws -> Payload {
        let parts = token.split(separator: ".")
        guard parts.count >= 2 else {
            throw APIError(status: 0, detail: "Token JWT inválido.")
        }
        var base64 = String(parts[1])
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        let pad = (4 - base64.count % 4) % 4
        base64 += String(repeating: "=", count: pad)
        guard let data = Data(base64Encoded: base64) else {
            throw APIError(status: 0, detail: "Não foi possível ler o JWT.")
        }
        return try JSONDecoder().decode(Payload.self, from: data)
    }
}
