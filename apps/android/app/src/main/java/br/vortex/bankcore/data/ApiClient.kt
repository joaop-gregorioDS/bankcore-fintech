package br.vortex.bankcore.data

import br.vortex.bankcore.BuildConfig
import br.vortex.bankcore.util.TaxId
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

class BankCoreApi(
    private val baseUrl: String = BuildConfig.API_BASE_URL,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(
                    HttpLoggingInterceptor().apply {
                        level = HttpLoggingInterceptor.Level.BASIC
                    },
                )
            }
        }
        .build()

    private val media = "application/json; charset=utf-8".toMediaType()

    fun login(taxId: String, password: String): TokenResponse =
        post(
            "/auth/login",
            mapOf("tax_id" to TaxId.digits(taxId), "password" to password),
            token = null,
        )

    fun register(taxId: String, fullName: String, email: String, password: String): UserProfile =
        post(
            "/auth/register",
            mapOf(
                "tax_id" to TaxId.digits(taxId),
                "full_name" to fullName,
                "email" to email,
                "password" to password,
            ),
            token = null,
        )

    fun me(token: String): UserProfile = get("/auth/me", token)

    fun directory(taxId: String, token: String): DirectoryEntry =
        get("/auth/directory/${TaxId.digits(taxId)}", token)

    fun createOrGetAccount(userId: String, token: String): Account =
        post("/accounts/", mapOf("user_id" to userId), token)

    fun account(id: String, token: String): Account = get("/accounts/$id", token)

    fun statement(accountId: String, token: String): List<LedgerTransaction> =
        get("/accounts/$accountId/statement", token)

    fun pix(
        sourceAccountId: String,
        destinationKey: String,
        amountReais: Double,
        description: String,
        token: String,
    ): LedgerTransaction = post(
        "/transactions/pix",
        mapOf(
            "source_account_id" to sourceAccountId,
            "destination_key" to TaxId.digits(destinationKey),
            "amount_reais" to amountReais,
            "idempotency_key" to Idempotency.pix(),
            "description" to description,
        ),
        token,
    )

    private inline fun <reified T> get(path: String, token: String?): T =
        send(path, "GET", null, token)

    private inline fun <reified T> post(path: String, body: Map<String, Any?>, token: String?): T =
        send(path, "POST", body, token)

    private inline fun <reified T> send(
        path: String,
        method: String,
        body: Map<String, Any?>?,
        token: String?,
    ): T {
        if (token.isNullOrBlank() && needsAuth(path)) {
            throw ApiException(401, "Token de acesso ausente.")
        }
        val url = baseUrl.trimEnd('/') + if (path.startsWith("/")) path else "/$path"
        val builder = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
        if (!token.isNullOrBlank()) {
            builder.header("Authorization", "Bearer $token")
        }
        if (body != null) {
            val obj = buildJsonObject {
                body.forEach { (k, v) ->
                    put(
                        k,
                        when (v) {
                            null -> JsonNull
                            is Int -> JsonPrimitive(v)
                            is Long -> JsonPrimitive(v)
                            is Double -> JsonPrimitive(v)
                            is Boolean -> JsonPrimitive(v)
                            else -> JsonPrimitive(v.toString())
                        },
                    )
                }
            }
            builder.header("Content-Type", "application/json")
            builder.method(method, obj.toString().toRequestBody(media))
        } else {
            builder.method(method, null)
        }
        client.newCall(builder.build()).execute().use { response ->
            val bytes = response.body?.string().orEmpty()
            if (response.code == 401) {
                throw ApiException(401, parseDetail(bytes) ?: "Token de acesso ausente.")
            }
            if (response.code !in 200..299) {
                throw ApiException(
                    response.code,
                    parseDetail(bytes) ?: "Falha na requisição (${response.code}).",
                )
            }
            return try {
                json.decodeFromString<T>(bytes)
            } catch (_: Exception) {
                throw ApiException(response.code, "Não foi possível ler a resposta da API.")
            }
        }
    }

    private fun needsAuth(path: String): Boolean =
        path.startsWith("/accounts") ||
            path.startsWith("/transactions") ||
            path.startsWith("/auth/me") ||
            path.startsWith("/auth/directory")

    private fun parseDetail(raw: String): String? {
        return try {
            val obj = json.parseToJsonElement(raw).jsonObject
            val detail = obj["detail"] ?: return null
            runCatching { detail.jsonPrimitive.content }.getOrNull()
                ?: runCatching {
                    detail.jsonArray.mapNotNull { item ->
                        runCatching { item.jsonObject["msg"]?.jsonPrimitive?.content }.getOrNull()
                    }.joinToString(" ").ifBlank { null }
                }.getOrNull()
        } catch (_: Exception) {
            null
        }
    }
}
