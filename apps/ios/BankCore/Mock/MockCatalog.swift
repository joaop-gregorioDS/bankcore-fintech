import Foundation
import SwiftUI

struct MockCatalog {
    let taxId: String
    let fullName: String
    let accountNumber: String

    var isJoao: Bool { taxId == APIConfig.joao.taxId }
    var isMaria: Bool { taxId == APIConfig.maria.taxId }

    var firstName: String {
        fullName.split(separator: " ").first.map(String.init) ?? "Correntista"
    }

    var initials: String {
        let parts = fullName.split(separator: " ").prefix(2)
        let letters = parts.compactMap { $0.first }
        return String(letters).uppercased()
    }

    var agency: String { "0001-9" }
    var maskedAccount: String {
        let digits = accountNumber.filter(\.isNumber)
        guard digits.count >= 4 else { return "Cc. •••••" }
        return "Ag. •••\(agency.suffix(3)) · Cc. •••••\(accountNumber.suffix(3))"
    }

    var segment: String {
        if isJoao { return "Vortex Carbon Black Corporate" }
        if isMaria { return "Vortex Carbon Platinum" }
        return "BankCore Demo"
    }

    var email: String {
        if isJoao { return "joao.paulo@vortexsoftware.com.br" }
        if isMaria { return "maria.silva@vortexsoftware.com.br" }
        return "correntista@bankcore.demo"
    }

    var pixLimit: Double { isJoao ? 50_000 : (isMaria ? 35_000 : 10_000) }

    var cards: [MockCard] {
        if isJoao {
            return [
                MockCard(
                    name: "Carbon Black",
                    last4: "4289",
                    holder: "JOAO PAULO",
                    invoice: 2_296.07,
                    dueLabel: "10 de setembro",
                    period: "30/Jul a 31/Ago",
                    used: 8_371,
                    available: 12_260,
                    total: 20_631,
                    brand: "Visa",
                    theme: .black
                ),
                MockCard(
                    name: "Carbon Virtual",
                    last4: "7712",
                    holder: "JOAO PAULO",
                    invoice: 412.90,
                    dueLabel: "10 de setembro",
                    period: "Fatura virtual",
                    used: 412.90,
                    available: 4_587.10,
                    total: 5_000,
                    brand: "Visa",
                    theme: .virtual
                ),
            ]
        }
        if isMaria {
            return [
                MockCard(
                    name: "Carbon Platinum",
                    last4: "8821",
                    holder: "MARIA SILVA",
                    invoice: 1_480.30,
                    dueLabel: "10 de setembro",
                    period: "30/Jul a 31/Ago",
                    used: 4_210,
                    available: 15_790,
                    total: 20_000,
                    brand: "Visa",
                    theme: .platinum
                ),
            ]
        }
        return [
            MockCard(
                name: "Carbon",
                last4: "0000",
                holder: fullName.uppercased(),
                invoice: 0,
                dueLabel: "—",
                period: "Demonstração",
                used: 0,
                available: 10_000,
                total: 10_000,
                brand: "Visa",
                theme: .virtual
            ),
        ]
    }

    var primaryCard: MockCard { cards[0] }

    var cardPurchases: [MockPurchase] {
        if isJoao {
            return [
                MockPurchase(merchant: "AWS Amazon Web Services", detail: "Crédito · 6x · 01/Set", amount: 1_240),
                MockPurchase(merchant: "Figma Inc.", detail: "Assinatura anual · 30/Ago", amount: 184.90),
                MockPurchase(merchant: "Latam Airlines", detail: "SP–FLN · 28/Ago", amount: 890.40),
                MockPurchase(merchant: "iFood Benefícios", detail: "Corporativo · 27/Ago", amount: 320),
                MockPurchase(merchant: "Apple.com/bill", detail: "iCloud+ · 25/Ago", amount: 42.90),
            ]
        }
        if isMaria {
            return [
                MockPurchase(merchant: "Latam Airlines Brasil", detail: "SP–RJ · 5x · 29/Ago", amount: 890),
                MockPurchase(merchant: "Farmácia Droga Raia", detail: "Crédito · 28/Ago", amount: 186.40),
                MockPurchase(merchant: "Uber *Trip", detail: "Deslocamento · 27/Ago", amount: 54.90),
                MockPurchase(merchant: "Netflix.com", detail: "Assinatura · 25/Ago", amount: 55.90),
                MockPurchase(merchant: "Padaria Bella Vista", detail: "Débito · 24/Ago", amount: 42.30),
            ]
        }
        return []
    }

    var dda: [MockBill] {
        if isJoao {
            return [
                MockBill(payee: "Amazon Web Services", due: "10/09/2026", amount: 650),
                MockBill(payee: "Contabilizei Tecnologia", due: "15/09/2026", amount: 189),
                MockBill(payee: "Vivo Fibra Empresas", due: "20/09/2026", amount: 249.90),
                MockBill(payee: "Google Workspace Business", due: "22/09/2026", amount: 72),
                MockBill(payee: "Serasa Experian PJ", due: "28/09/2026", amount: 119.90),
            ]
        }
        if isMaria {
            return [
                MockBill(payee: "Condomínio Edifício Paulista", due: "08/09/2026", amount: 650),
                MockBill(payee: "Unimed Saúde Corporativo", due: "12/09/2026", amount: 890),
                MockBill(payee: "Enel Energia", due: "18/09/2026", amount: 312.45),
                MockBill(payee: "Claro Residencial", due: "22/09/2026", amount: 129.90),
            ]
        }
        return []
    }

    var scheduledTotal: Double {
        dda.reduce(0) { $0 + $1.amount }
    }

    var investments: [MockInvestment] {
        if isJoao {
            return [
                MockInvestment(name: "CDB Vortex 102% CDI", amount: 12_400, yield: "+1,12% m."),
                MockInvestment(name: "Tesouro Selic 2029", amount: 8_200, yield: "+0,89% m."),
                MockInvestment(name: "Fundo Carbon RF", amount: 3_150, yield: "+0,74% m."),
            ]
        }
        if isMaria {
            return [
                MockInvestment(name: "CDB Liquidez diária", amount: 8_500, yield: "+0,98% m."),
                MockInvestment(name: "Tesouro Selic 2029", amount: 4_100, yield: "+0,89% m."),
            ]
        }
        return [
            MockInvestment(name: "CDB Boas-vindas", amount: 0, yield: "—"),
        ]
    }

    var investTotal: Double { investments.reduce(0) { $0 + $1.amount } }

    var creditLimit: Double { pixLimit }
    var creditUsed: Double { isJoao ? 0 : 0 }

    var notifications: [MockNotice] {
        [
            MockNotice(
                title: "Pix recebido no ledger",
                body: "Há lançamentos novos no extrato da conta \(accountNumber).",
                time: "agora",
                icon: "arrow.down.left",
                simulated: false
            ),
            MockNotice(
                title: "Fatura Carbon vence dia 10",
                body: "Fatura de \(Money.reais(primaryCard.invoice)). Módulo simulado — não liquida no ledger.",
                time: "hoje",
                icon: "creditcard",
                simulated: true
            ),
            MockNotice(
                title: "\(dda.count) boletos na agenda DDA",
                body: "Total agendado \(Money.reais(scheduledTotal)). Simulação de UX.",
                time: "ontem",
                icon: "doc.text",
                simulated: true
            ),
            MockNotice(
                title: "BankCore Invest",
                body: "Posição de \(Money.reais(investTotal)) · rendimento ilustrativo.",
                time: "2 d",
                icon: "chart.line.uptrend.xyaxis",
                simulated: true
            ),
        ]
    }

    var promoTitle: String { "CDB 102% do CDI na sua conta?" }
    var promoBody: String { "Simule R$ 100/mês no BankCore Invest. Módulo didático — não grava no ledger." }
}

struct MockCard: Identifiable, Hashable {
    var id: String { last4 + name }
    let name: String
    let last4: String
    let holder: String
    let invoice: Double
    let dueLabel: String
    let period: String
    let used: Double
    let available: Double
    let total: Double
    let brand: String
    let theme: Theme

    enum Theme: Hashable {
        case black, platinum, virtual
    }

    var usedRatio: Double {
        guard total > 0 else { return 0 }
        return min(1, used / total)
    }
}

struct MockPurchase: Identifiable, Hashable {
    var id: String { merchant + detail }
    let merchant: String
    let detail: String
    let amount: Double
}

struct MockBill: Identifiable, Hashable {
    var id: String { payee + due }
    let payee: String
    let due: String
    let amount: Double
}

struct MockInvestment: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let amount: Double
    let yield: String
}

struct MockNotice: Identifiable, Hashable {
    var id: String { title }
    let title: String
    let body: String
    let time: String
    let icon: String
    let simulated: Bool
}

enum LastAccountStore {
    private static let key = "bankcore.lastTaxId"

    static var taxId: String? {
        get { UserDefaults.standard.string(forKey: key) }
        set { UserDefaults.standard.set(newValue, forKey: key) }
    }
}
