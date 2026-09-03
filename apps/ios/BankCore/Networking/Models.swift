import Foundation

struct TokenResponse: Decodable {
    let accessToken: String
    let tokenType: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

struct UserProfile: Decodable, Equatable {
    let id: UUID
    let taxId: String
    let fullName: String
    let email: String
    let isActive: Bool
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, email
        case taxId = "tax_id"
        case fullName = "full_name"
        case isActive = "is_active"
        case createdAt = "created_at"
    }
}

struct DirectoryEntry: Decodable, Equatable {
    let userId: UUID
    let taxId: String
    let fullName: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case taxId = "tax_id"
        case fullName = "full_name"
    }
}

struct Account: Decodable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let accountNumber: String
    let balanceReais: Double
    let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case accountNumber = "account_number"
        case balanceReais = "balance_reais"
        case isActive = "is_active"
    }
}

struct LedgerTransaction: Decodable, Equatable, Identifiable, Hashable {
    let transactionId: UUID
    let idempotencyKey: String
    let sourceAccountId: UUID?
    let destinationAccountId: UUID?
    let amountReais: Double
    let transactionType: String
    let direction: String
    let status: String
    let createdAt: Date
    let description: String?

    var id: UUID { transactionId }
    var isCredit: Bool { direction.uppercased() == "CREDIT" }

    var title: String {
        if let description, !description.isEmpty { return description }
        if transactionType.uppercased() == "DEPOSIT" { return "Depósito" }
        return isCredit ? "Pix recebido" : "Pix enviado"
    }

    var typeLabel: String {
        if transactionType.uppercased() == "DEPOSIT" { return "Depósito" }
        return isCredit ? "Pix recebido" : "Pix enviado"
    }

    enum CodingKeys: String, CodingKey {
        case transactionId = "transaction_id"
        case idempotencyKey = "idempotency_key"
        case sourceAccountId = "source_account_id"
        case destinationAccountId = "destination_account_id"
        case amountReais = "amount_reais"
        case transactionType = "transaction_type"
        case direction, status, description
        case createdAt = "created_at"
    }
}

struct Session: Equatable {
    var token: String
    var userId: UUID
    var taxId: String
    var fullName: String
    var email: String?
}

enum Idempotency {
    static func pix() -> String { "pix_\(UUID().uuidString)" }
    static func deposit() -> String { "dep_\(UUID().uuidString)" }
}
