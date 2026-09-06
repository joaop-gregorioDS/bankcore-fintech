package br.vortex.bankcore.data

import br.vortex.bankcore.util.Money

data class MockCard(
    val name: String,
    val last4: String,
    val holder: String,
    val invoice: Double,
    val dueLabel: String,
    val period: String,
    val used: Double,
    val available: Double,
    val total: Double,
    val brand: String,
    val theme: Theme,
) {
    enum class Theme { BLACK, PLATINUM, VIRTUAL }
    val id: String get() = last4 + name
    val usedRatio: Double get() = if (total <= 0) 0.0 else minOf(1.0, used / total)
}

data class MockPurchase(val merchant: String, val detail: String, val amount: Double) {
    val id: String get() = merchant + detail
}

data class MockBill(val payee: String, val due: String, val amount: Double) {
    val id: String get() = payee + due
}

data class MockInvestment(val name: String, val amount: Double, val yield: String) {
    val id: String get() = name
}

data class MockNotice(
    val title: String,
    val body: String,
    val time: String,
    val icon: String,
    val simulated: Boolean,
) {
    val id: String get() = title
}

data class MockCatalog(
    val taxId: String,
    val fullName: String,
    val accountNumber: String,
) {
    val isLucas: Boolean get() = taxId == ApiConfig.lucas.taxId
    val isMaria: Boolean get() = taxId == ApiConfig.maria.taxId

    val firstName: String
        get() = fullName.split(" ").firstOrNull().orEmpty().ifBlank { "Correntista" }

    val initials: String
        get() = fullName.split(" ").take(2).mapNotNull { it.firstOrNull() }
            .joinToString("").uppercase()

    val agency: String = "0001-9"

    val segment: String
        get() = when {
            isLucas -> "Vortex Carbon Black Corporate"
            isMaria -> "Vortex Carbon Platinum"
            else -> "BankCore Demo"
        }

    val email: String
        get() = when {
            isLucas -> ApiConfig.CONTACT_EMAIL
            isMaria -> "maria.silva@vortexsoftware.tech"
            else -> "correntista@bankcore.demo"
        }

    val pixLimit: Double
        get() = when {
            isLucas -> 50_000.0
            isMaria -> 35_000.0
            else -> 10_000.0
        }

    val cards: List<MockCard>
        get() = when {
            isLucas -> listOf(
                MockCard(
                    name = "Carbon Black",
                    last4 = "4289",
                    holder = "LUCAS MENDES",
                    invoice = 2_296.07,
                    dueLabel = "10 de setembro",
                    period = "30/Jul a 31/Ago",
                    used = 8_371.0,
                    available = 12_260.0,
                    total = 20_631.0,
                    brand = "Visa",
                    theme = MockCard.Theme.BLACK,
                ),
                MockCard(
                    name = "Carbon Virtual",
                    last4 = "7712",
                    holder = "LUCAS MENDES",
                    invoice = 412.90,
                    dueLabel = "10 de setembro",
                    period = "Fatura virtual",
                    used = 412.90,
                    available = 4_587.10,
                    total = 5_000.0,
                    brand = "Visa",
                    theme = MockCard.Theme.VIRTUAL,
                ),
            )
            isMaria -> listOf(
                MockCard(
                    name = "Carbon Platinum",
                    last4 = "8821",
                    holder = "MARIA SILVA",
                    invoice = 1_480.30,
                    dueLabel = "10 de setembro",
                    period = "30/Jul a 31/Ago",
                    used = 4_210.0,
                    available = 15_790.0,
                    total = 20_000.0,
                    brand = "Visa",
                    theme = MockCard.Theme.PLATINUM,
                ),
            )
            else -> listOf(
                MockCard(
                    name = "Carbon",
                    last4 = "0000",
                    holder = fullName.uppercase(),
                    invoice = 0.0,
                    dueLabel = "—",
                    period = "Demonstração",
                    used = 0.0,
                    available = 10_000.0,
                    total = 10_000.0,
                    brand = "Visa",
                    theme = MockCard.Theme.VIRTUAL,
                ),
            )
        }

    val primaryCard: MockCard get() = cards.first()

    val cardPurchases: List<MockPurchase>
        get() = when {
            isLucas -> listOf(
                MockPurchase("AWS Amazon Web Services", "Crédito · 6x · 01/Set", 1_240.0),
                MockPurchase("Figma Inc.", "Assinatura anual · 30/Ago", 184.90),
                MockPurchase("Latam Airlines", "SP–FLN · 28/Ago", 890.40),
                MockPurchase("iFood Benefícios", "Corporativo · 27/Ago", 320.0),
                MockPurchase("Apple.com/bill", "iCloud+ · 25/Ago", 42.90),
            )
            isMaria -> listOf(
                MockPurchase("Latam Airlines Brasil", "SP–RJ · 5x · 29/Ago", 890.0),
                MockPurchase("Farmácia Droga Raia", "Crédito · 28/Ago", 186.40),
                MockPurchase("Uber *Trip", "Deslocamento · 27/Ago", 54.90),
                MockPurchase("Netflix.com", "Assinatura · 25/Ago", 55.90),
                MockPurchase("Padaria Bella Vista", "Débito · 24/Ago", 42.30),
            )
            else -> emptyList()
        }

    val dda: List<MockBill>
        get() = when {
            isLucas -> listOf(
                MockBill("Amazon Web Services", "10/09/2026", 650.0),
                MockBill("Contabilizei Tecnologia", "15/09/2026", 189.0),
                MockBill("Vivo Fibra Empresas", "20/09/2026", 249.90),
                MockBill("Google Workspace Business", "22/09/2026", 72.0),
                MockBill("Serasa Experian PJ", "28/09/2026", 119.90),
            )
            isMaria -> listOf(
                MockBill("Condomínio Edifício Paulista", "08/09/2026", 650.0),
                MockBill("Unimed Saúde Corporativo", "12/09/2026", 890.0),
                MockBill("Enel Energia", "18/09/2026", 312.45),
                MockBill("Claro Residencial", "22/09/2026", 129.90),
            )
            else -> emptyList()
        }

    val scheduledTotal: Double get() = dda.sumOf { it.amount }

    val investments: List<MockInvestment>
        get() = when {
            isLucas -> listOf(
                MockInvestment("CDB Vortex 102% CDI", 12_400.0, "+1,12% m."),
                MockInvestment("Tesouro Selic 2029", 8_200.0, "+0,89% m."),
                MockInvestment("Fundo Carbon RF", 3_150.0, "+0,74% m."),
            )
            isMaria -> listOf(
                MockInvestment("CDB Liquidez diária", 8_500.0, "+0,98% m."),
                MockInvestment("Tesouro Selic 2029", 4_100.0, "+0,89% m."),
            )
            else -> listOf(MockInvestment("CDB Boas-vindas", 0.0, "—"))
        }

    val investTotal: Double get() = investments.sumOf { it.amount }
    val creditLimit: Double get() = pixLimit

    val notifications: List<MockNotice>
        get() = listOf(
            MockNotice(
                title = "Pix recebido no ledger",
                body = "Há lançamentos novos no extrato da conta $accountNumber.",
                time = "agora",
                icon = "incoming",
                simulated = false,
            ),
            MockNotice(
                title = "Fatura Carbon vence dia 10",
                body = "Fatura de ${Money.reais(primaryCard.invoice)}. Módulo simulado — não liquida no ledger.",
                time = "hoje",
                icon = "card",
                simulated = true,
            ),
            MockNotice(
                title = "${dda.size} boletos na agenda DDA",
                body = "Total agendado ${Money.reais(scheduledTotal)}. Simulação de UX.",
                time = "ontem",
                icon = "doc",
                simulated = true,
            ),
            MockNotice(
                title = "BankCore Invest",
                body = "Posição de ${Money.reais(investTotal)} · rendimento ilustrativo.",
                time = "2 d",
                icon = "chart",
                simulated = true,
            ),
        )

    val promoTitle: String = "CDB 102% do CDI na sua conta?"
    val promoBody: String = "Simule R$ 100/mês no BankCore Invest. Módulo didático — não grava no ledger."
}
