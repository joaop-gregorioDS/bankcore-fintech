package br.vortex.bankcore.data

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import android.util.Base64
import java.nio.charset.StandardCharsets

data class JwtPayload(
    val sub: String?,
    val taxId: String?,
    val name: String?,
    val exp: Long?,
) {
    val userId: String? get() = sub
    val isExpired: Boolean
        get() = exp != null && System.currentTimeMillis() / 1000 >= exp
}

object Jwt {
    fun payload(token: String): JwtPayload {
        val parts = token.split('.')
        if (parts.size < 2) throw ApiException(0, "Token JWT inválido.")
        var base64 = parts[1].replace('-', '+').replace('_', '/')
        val pad = (4 - base64.length % 4) % 4
        base64 += "=".repeat(pad)
        val json = try {
            String(Base64.decode(base64, Base64.DEFAULT), StandardCharsets.UTF_8)
        } catch (_: Exception) {
            throw ApiException(0, "Não foi possível ler o JWT.")
        }
        val obj = Json.parseToJsonElement(json).jsonObject
        return JwtPayload(
            sub = obj["sub"]?.jsonPrimitive?.contentOrNull,
            taxId = obj["tax_id"]?.jsonPrimitive?.contentOrNull,
            name = obj["name"]?.jsonPrimitive?.contentOrNull,
            exp = obj["exp"]?.jsonPrimitive?.longOrNull,
        )
    }
}
