package br.vortex.bankcore.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "bankcore_prefs")

class PrefsStore(private val context: Context) {
    private val store get() = context.applicationContext.dataStore

    suspend fun isDark(): Boolean =
        store.data.map { it[DARK] ?: false }.first()

    suspend fun setDark(value: Boolean) {
        store.edit { it[DARK] = value }
    }

    suspend fun lastTaxId(): String? =
        store.data.map { it[LAST_TAX] }.first()

    suspend fun setLastTaxId(value: String?) {
        store.edit {
            if (value.isNullOrBlank()) it.remove(LAST_TAX) else it[LAST_TAX] = value
        }
    }

    suspend fun isBalanceHidden(): Boolean =
        store.data.map { it[HIDDEN] ?: false }.first()

    suspend fun setBalanceHidden(value: Boolean) {
        store.edit { it[HIDDEN] = value }
    }

    private companion object {
        val DARK = booleanPreferencesKey("uses_dark_appearance")
        val LAST_TAX = stringPreferencesKey("last_tax_id")
        val HIDDEN = booleanPreferencesKey("balance_hidden")
    }
}
