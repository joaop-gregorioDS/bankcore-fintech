package br.vortex.bankcore.data

object ApiConfig {
    const val HOST = "bankcore.vortexsoftware.tech"
    const val BASE_URL = "https://bankcore.vortexsoftware.tech"
    const val APP_VERSION = "1.10.25"
    const val LEGAL_NAME = "Vortex Software LTDA"
    const val CONTACT_EMAIL = "contato@vortexsoftware.tech"

    data class DemoAccount(
        val name: String,
        val taxId: String,
        val password: String,
        val initials: String,
    )

    val lucas = DemoAccount(
        name = "Lucas Mendes Rocha",
        taxId = "98765432100",
        password = "teste123456",
        initials = "LM",
    )

    val maria = DemoAccount(
        name = "Maria Silva",
        taxId = "12345678900",
        password = "teste123456",
        initials = "MS",
    )
}
