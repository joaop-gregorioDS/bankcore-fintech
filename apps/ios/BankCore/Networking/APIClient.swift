import Foundation

struct APIError: Error, LocalizedError, Equatable {
    let status: Int
    let detail: String
    var errorDescription: String? { detail }
}

struct BankCoreAPI {
    var session: URLSession = .shared

    func login(taxId: String, password: String) async throws -> TokenResponse {
        try await post(
            "/auth/login",
            body: ["tax_id": TaxID.digits(taxId), "password": password],
            token: nil
        )
    }

    func register(taxId: String, fullName: String, email: String, password: String) async throws -> UserProfile {
        try await post(
            "/auth/register",
            body: [
                "tax_id": TaxID.digits(taxId),
                "full_name": fullName,
                "email": email,
                "password": password,
            ],
            token: nil
        )
    }

    func me(token: String) async throws -> UserProfile {
        try await get("/auth/me", token: token)
    }

    func directory(taxId: String, token: String) async throws -> DirectoryEntry {
        try await get("/auth/directory/\(TaxID.digits(taxId))", token: token)
    }

    func createOrGetAccount(userId: UUID, token: String) async throws -> Account {
        try await post("/accounts/", body: ["user_id": userId.uuidString], token: token)
    }

    func account(id: UUID, token: String) async throws -> Account {
        try await get("/accounts/\(id.uuidString)", token: token)
    }

    func statement(accountId: UUID, token: String) async throws -> [LedgerTransaction] {
        try await get("/accounts/\(accountId.uuidString)/statement", token: token)
    }

    func pix(
        sourceAccountId: UUID,
        destinationKey: String,
        amountReais: Double,
        description: String,
        token: String
    ) async throws -> LedgerTransaction {
        try await post(
            "/transactions/pix",
            body: [
                "source_account_id": sourceAccountId.uuidString,
                "destination_key": TaxID.digits(destinationKey),
                "amount_reais": amountReais,
                "idempotency_key": Idempotency.pix(),
                "description": description,
            ],
            token: token
        )
    }

    private func get<T: Decodable>(_ path: String, token: String?) async throws -> T {
        try await send(path, method: "GET", body: nil as [String: Any]?, token: token)
    }

    private func post<T: Decodable>(_ path: String, body: [String: Any], token: String?) async throws -> T {
        try await send(path, method: "POST", body: body, token: token)
    }

    private func send<T: Decodable>(
        _ path: String,
        method: String,
        body: [String: Any]?,
        token: String?
    ) async throws -> T {
        if token == nil, needsAuth(path) {
            throw APIError(status: 401, detail: "Token de acesso ausente.")
        }

        var request = URLRequest(url: APIConfig.url(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError(status: 0, detail: "Resposta inválida do servidor.")
        }
        if http.statusCode == 401 {
            throw APIError(status: 401, detail: Self.parseDetail(data) ?? "Token de acesso ausente.")
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError(status: http.statusCode, detail: Self.parseDetail(data) ?? "Falha na requisição (\(http.statusCode)).")
        }
        do {
            return try BankJSON.decoder.decode(T.self, from: data)
        } catch {
            throw APIError(status: http.statusCode, detail: "Não foi possível ler a resposta da API.")
        }
    }

    private func needsAuth(_ path: String) -> Bool {
        path.hasPrefix("/accounts")
            || path.hasPrefix("/transactions")
            || path.hasPrefix("/auth/me")
            || path.hasPrefix("/auth/directory")
    }

    static func parseDetail(_ data: Data) -> String? {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return nil
        }
        if let detail = object["detail"] as? String {
            return detail
        }
        if let items = object["detail"] as? [[String: Any]] {
            let messages = items.compactMap { $0["msg"] as? String }
            if !messages.isEmpty { return messages.joined(separator: " ") }
        }
        return nil
    }
}

enum BankJSON {
    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let raw = try container.decode(String.self)
            if let date = BankDate.parseAPI(raw) { return date }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unrecognized date: \(raw)"
            )
        }
        return decoder
    }()
}
