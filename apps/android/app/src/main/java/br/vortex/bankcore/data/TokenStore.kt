package br.vortex.bankcore.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * JWT in EncryptedSharedPreferences (Android Keystore AES256-GCM).
 * Financial routes must not be called without a token from here.
 */
class TokenStore(context: Context) {
    private val prefs: SharedPreferences

    init {
        val masterKey = MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        prefs = EncryptedSharedPreferences.create(
            context.applicationContext,
            "bankcore_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun read(): String? = prefs.getString(KEY, null)?.takeIf { it.isNotBlank() }

    fun write(token: String?) {
        prefs.edit().apply {
            if (token.isNullOrBlank()) remove(KEY) else putString(KEY, token)
        }.apply()
    }

    fun clear() = write(null)

    private companion object {
        const val KEY = "access_token"
    }
}
