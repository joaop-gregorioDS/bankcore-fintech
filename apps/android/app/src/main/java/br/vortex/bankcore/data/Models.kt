package br.vortex.bankcore.data

import br.vortex.bankcore.util.BankDate
import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import java.time.Instant
import java.util.UUID

object InstantAsStringSerializer : KSerializer<Instant> {
    override val descriptor = PrimitiveSerialDescriptor("Instant", PrimitiveKind.STRING)
    override fun serialize(encoder: Encoder, value: Instant) = encoder.encodeString(value.toString())
    override fun deserialize(decoder: Decoder): Instant = BankDate.parseApi(decoder.decodeString())
}

@Serializable
data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Int = 3600,
)

@Serializable
data class UserProfile(
    val id: String,
    @SerialName("tax_id") val taxId: String,
    @SerialName("full_name") val fullName: String,
    val email: String,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at")
    @Serializable(with = InstantAsStringSerializer::class)
    val createdAt: Instant = Instant.now(),
)

@Serializable
data class DirectoryEntry(
    @SerialName("user_id") val userId: String,
    @SerialName("tax_id") val taxId: String,
    @SerialName("full_name") val fullName: String,
)

@Serializable
data class Account(
    val id: String,
    @SerialName("user_id") val userId: String,
    @SerialName("account_number") val accountNumber: String,
    @SerialName("balance_reais") val balanceReais: Double,
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class LedgerTransaction(
    @SerialName("transaction_id") val transactionId: String,
    @SerialName("idempotency_key") val idempotencyKey: String,
    @SerialName("source_account_id") val sourceAccountId: String? = null,
    @SerialName("destination_account_id") val destinationAccountId: String? = null,
    @SerialName("amount_reais") val amountReais: Double,
    @SerialName("transaction_type") val transactionType: String,
    val direction: String,
    val status: String,
    @SerialName("created_at")
    @Serializable(with = InstantAsStringSerializer::class)
    val createdAt: Instant,
    val description: String? = null,
) {
    val isCredit: Boolean get() = direction.equals("CREDIT", ignoreCase = true)

    val title: String
        get() {
            if (!description.isNullOrBlank()) return description
            if (transactionType.equals("DEPOSIT", ignoreCase = true)) return "Depósito"
            return if (isCredit) "Pix recebido" else "Pix enviado"
        }

    val typeLabel: String
        get() {
            if (transactionType.equals("DEPOSIT", ignoreCase = true)) return "Depósito"
            return if (isCredit) "Pix recebido" else "Pix enviado"
        }
}

data class Session(
    val token: String,
    val userId: String,
    val taxId: String,
    val fullName: String,
    val email: String? = null,
)

object Idempotency {
    fun pix(): String = "pix_${UUID.randomUUID()}"
    fun deposit(): String = "dep_${UUID.randomUUID()}"
}

class ApiException(val status: Int, val detail: String) : Exception(detail)
