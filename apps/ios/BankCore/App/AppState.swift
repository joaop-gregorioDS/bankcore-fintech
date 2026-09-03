import Foundation
import Observation

@Observable
@MainActor
final class AppState {
    var session: Session?
    var account: Account?
    var statement: [LedgerTransaction] = []
    var isRestoring = true
    var isBusy = false
    var errorMessage: String?
    var selectedTab: MainTab = .home
    var presentedReceipt: LedgerTransaction?
    var isBalanceHidden = false

    private let api = BankCoreAPI()

    enum MainTab: Hashable {
        case home, pix, statement
    }

    var isLoggedIn: Bool { session != nil }

    func bootstrap() async {
        isRestoring = true
        defer { isRestoring = false }
        #if DEBUG
        if ProcessInfo.processInfo.environment["BANKCORE_DEMO"] == "joao" {
            await loginDemo(APIConfig.joao)
            return
        }
        if ProcessInfo.processInfo.environment["BANKCORE_DEMO"] == "maria" {
            await loginDemo(APIConfig.maria)
            return
        }
        #endif
        guard let token = KeychainStore.read(), !token.isEmpty else { return }
        do {
            let payload = try JWT.payload(from: token)
            if payload.isExpired {
                logout()
                return
            }
            try await establishSession(token: token, payload: payload)
        } catch {
            logout()
        }
    }

    func login(taxId: String, password: String) async {
        errorMessage = nil
        isBusy = true
        defer { isBusy = false }
        do {
            let token = try await api.login(taxId: taxId, password: password)
            let payload = try JWT.payload(from: token.accessToken)
            try await establishSession(token: token.accessToken, payload: payload)
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func loginDemo(_ demo: APIConfig.DemoAccount) async {
        await login(taxId: demo.taxId, password: demo.password)
    }

    func register(taxId: String, fullName: String, email: String, password: String) async {
        errorMessage = nil
        isBusy = true
        defer { isBusy = false }
        do {
            _ = try await api.register(taxId: taxId, fullName: fullName, email: email, password: password)
            await login(taxId: taxId, password: password)
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func logout() {
        KeychainStore.clear()
        session = nil
        account = nil
        statement = []
        presentedReceipt = nil
        selectedTab = .home
        errorMessage = nil
    }

    func refresh() async {
        guard let session, let account else { return }
        do {
            self.account = try await api.account(id: account.id, token: session.token)
            statement = try await api.statement(accountId: account.id, token: session.token)
        } catch let error as APIError where error.status == 401 {
            logout()
            errorMessage = error.detail
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func lookupPix(taxId: String) async throws -> DirectoryEntry {
        guard let session else {
            throw APIError(status: 401, detail: "Token de acesso ausente.")
        }
        return try await api.directory(taxId: taxId, token: session.token)
    }

    func sendPix(destinationKey: String, amountReais: Double, description: String) async throws -> LedgerTransaction {
        guard let session else {
            throw APIError(status: 401, detail: "Token de acesso ausente.")
        }
        guard let account else {
            throw APIError(status: 0, detail: "Conta não carregada.")
        }
        let tx = try await api.pix(
            sourceAccountId: account.id,
            destinationKey: destinationKey,
            amountReais: amountReais,
            description: description,
            token: session.token
        )
        await refresh()
        presentedReceipt = tx
        selectedTab = .statement
        return tx
    }

    func openReceipt(_ tx: LedgerTransaction) {
        presentedReceipt = tx
    }

    private func establishSession(token: String, payload: JWT.Payload) async throws {
        guard let userId = payload.userId else {
            throw APIError(status: 0, detail: "Token sem identificação de correntista.")
        }
        KeychainStore.write(token)
        var next = Session(
            token: token,
            userId: userId,
            taxId: TaxID.digits(payload.taxId ?? ""),
            fullName: payload.name ?? "Correntista BankCore"
        )
        if let profile = try? await api.me(token: token) {
            next.taxId = profile.taxId
            next.fullName = profile.fullName
            next.email = profile.email
        }
        session = next
        account = try await api.createOrGetAccount(userId: userId, token: token)
        statement = try await api.statement(accountId: account!.id, token: token)
        errorMessage = nil
        selectedTab = .home
    }
}
