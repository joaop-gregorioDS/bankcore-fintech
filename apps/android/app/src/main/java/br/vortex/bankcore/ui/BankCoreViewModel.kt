package br.vortex.bankcore.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import br.vortex.bankcore.data.Account
import br.vortex.bankcore.data.ApiConfig
import br.vortex.bankcore.data.ApiException
import br.vortex.bankcore.data.BankCoreApi
import br.vortex.bankcore.data.DirectoryEntry
import br.vortex.bankcore.data.Jwt
import br.vortex.bankcore.data.LedgerTransaction
import br.vortex.bankcore.data.MockCatalog
import br.vortex.bankcore.data.PrefsStore
import br.vortex.bankcore.data.Session
import br.vortex.bankcore.data.TokenStore
import br.vortex.bankcore.util.TaxId
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant

enum class MainTab { Home, Pix, Statement, Cards, Profile }

enum class Hub { Pay, Invest, Credit, More, Notifications, Invoice, Dda }

data class UiState(
    val isRestoring: Boolean = true,
    val isBusy: Boolean = false,
    val session: Session? = null,
    val account: Account? = null,
    val statement: List<LedgerTransaction> = emptyList(),
    val selectedTab: MainTab = MainTab.Home,
    val presentedReceipt: LedgerTransaction? = null,
    val presentedHub: Hub? = null,
    val isBalanceHidden: Boolean = false,
    val toast: String? = null,
    val errorMessage: String? = null,
    val usesDarkAppearance: Boolean = false,
    val lastSeen: Instant = Instant.now(),
    val lastTaxId: String? = null,
)

class BankCoreViewModel(application: Application) : AndroidViewModel(application) {
    private val api = BankCoreApi()
    private val tokens = TokenStore(application)
    private val prefs = PrefsStore(application)

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var toastJob: Job? = null
    private var openPixAfterLogin = false

    val mock: MockCatalog
        get() {
            val s = _state.value
            return MockCatalog(
                taxId = s.session?.taxId.orEmpty(),
                fullName = s.session?.fullName ?: "Correntista BankCore",
                accountNumber = s.account?.accountNumber ?: "—",
            )
        }

    init {
        viewModelScope.launch { bootstrap() }
    }

    private suspend fun bootstrap() {
        _state.update { it.copy(isRestoring = true) }
        val dark = prefs.isDark()
        val hidden = prefs.isBalanceHidden()
        val last = prefs.lastTaxId()
        _state.update {
            it.copy(
                usesDarkAppearance = dark,
                isBalanceHidden = hidden,
                lastTaxId = last,
            )
        }
        val token = tokens.read()
        if (token.isNullOrBlank()) {
            _state.update { it.copy(isRestoring = false) }
            return
        }
        try {
            val payload = Jwt.payload(token)
            if (payload.isExpired || payload.userId.isNullOrBlank()) {
                logout()
                _state.update { it.copy(isRestoring = false) }
                return
            }
            withContext(Dispatchers.IO) { establishSession(token, payload.userId!!, payload) }
        } catch (_: Exception) {
            logout()
        } finally {
            _state.update { it.copy(isRestoring = false) }
        }
    }

    fun login(taxId: String, password: String) {
        viewModelScope.launch {
            _state.update { it.copy(errorMessage = null, isBusy = true) }
            try {
                val token = withContext(Dispatchers.IO) {
                    api.login(taxId, password).accessToken
                }
                val payload = Jwt.payload(token)
                val userId = payload.userId
                    ?: throw ApiException(0, "Token sem identificação de correntista.")
                withContext(Dispatchers.IO) { establishSession(token, userId, payload) }
            } catch (e: Exception) {
                _state.update { it.copy(errorMessage = e.message ?: e.toString()) }
            } finally {
                _state.update { it.copy(isBusy = false) }
            }
        }
    }

    fun loginDemo(demo: ApiConfig.DemoAccount) = login(demo.taxId, demo.password)

    fun loginDemoAndOpenPix(demo: ApiConfig.DemoAccount) {
        openPixAfterLogin = true
        loginDemo(demo)
    }

    fun register(taxId: String, fullName: String, email: String, password: String) {
        viewModelScope.launch {
            _state.update { it.copy(errorMessage = null, isBusy = true) }
            try {
                withContext(Dispatchers.IO) {
                    api.register(taxId, fullName, email, password)
                }
                login(taxId, password)
            } catch (e: Exception) {
                _state.update { it.copy(errorMessage = e.message ?: e.toString(), isBusy = false) }
            }
        }
    }

    fun logout() {
        val taxId = _state.value.session?.taxId
        tokens.clear()
        if (!taxId.isNullOrBlank()) {
            viewModelScope.launch { prefs.setLastTaxId(taxId) }
        }
        _state.update {
            it.copy(
                session = null,
                account = null,
                statement = emptyList(),
                presentedReceipt = null,
                presentedHub = null,
                selectedTab = MainTab.Home,
                errorMessage = null,
                lastTaxId = taxId ?: it.lastTaxId,
            )
        }
    }

    fun flash(message: String) {
        toastJob?.cancel()
        _state.update { it.copy(toast = message) }
        toastJob = viewModelScope.launch {
            delay(2_200)
            _state.update { current ->
                if (current.toast == message) current.copy(toast = null) else current
            }
        }
    }

    fun simulate(message: String) = flash(message)

    fun selectTab(tab: MainTab) = _state.update { it.copy(selectedTab = tab) }

    fun openHub(hub: Hub) = _state.update { it.copy(presentedHub = hub) }

    fun dismissHub() = _state.update { it.copy(presentedHub = null) }

    fun openReceipt(tx: LedgerTransaction) = _state.update { it.copy(presentedReceipt = tx) }

    fun dismissReceipt() = _state.update { it.copy(presentedReceipt = null) }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun toggleBalanceHidden() {
        val next = !_state.value.isBalanceHidden
        _state.update { it.copy(isBalanceHidden = next) }
        viewModelScope.launch { prefs.setBalanceHidden(next) }
    }

    fun setDarkAppearance(value: Boolean) {
        _state.update { it.copy(usesDarkAppearance = value) }
        viewModelScope.launch { prefs.setDark(value) }
    }

    fun refresh() {
        viewModelScope.launch { refreshNow() }
    }

    private suspend fun refreshNow() {
        val session = _state.value.session ?: return
        val account = _state.value.account ?: return
        try {
            val next = withContext(Dispatchers.IO) {
                api.account(account.id, session.token) to api.statement(account.id, session.token)
            }
            _state.update { it.copy(account = next.first, statement = next.second) }
        } catch (e: ApiException) {
            if (e.status == 401) {
                logout()
                _state.update { it.copy(errorMessage = e.detail) }
            } else {
                _state.update { it.copy(errorMessage = e.detail) }
            }
        } catch (e: Exception) {
            _state.update { it.copy(errorMessage = e.message ?: e.toString()) }
        }
    }

    suspend fun lookupPix(taxId: String): DirectoryEntry {
        val session = _state.value.session
            ?: throw ApiException(401, "Token de acesso ausente.")
        return withContext(Dispatchers.IO) { api.directory(taxId, session.token) }
    }

    suspend fun sendPix(destinationKey: String, amountReais: Double, description: String): LedgerTransaction {
        val session = _state.value.session
            ?: throw ApiException(401, "Token de acesso ausente.")
        val account = _state.value.account
            ?: throw ApiException(0, "Conta não carregada.")
        val tx = withContext(Dispatchers.IO) {
            api.pix(
                sourceAccountId = account.id,
                destinationKey = destinationKey,
                amountReais = amountReais,
                description = description,
                token = session.token,
            )
        }
        refreshNow()
        _state.update { it.copy(presentedReceipt = tx, selectedTab = MainTab.Statement) }
        return tx
    }

    private fun establishSession(token: String, userId: String, payload: br.vortex.bankcore.data.JwtPayload) {
        tokens.write(token)
        var next = Session(
            token = token,
            userId = userId,
            taxId = TaxId.digits(payload.taxId.orEmpty()),
            fullName = payload.name ?: "Correntista BankCore",
        )
        runCatching { api.me(token) }.getOrNull()?.let { profile ->
            next = next.copy(
                taxId = profile.taxId,
                fullName = profile.fullName,
                email = profile.email,
            )
        }
        val account = api.createOrGetAccount(userId, token)
        val statement = api.statement(account.id, token)
        val tab = if (openPixAfterLogin) MainTab.Pix else MainTab.Home
        openPixAfterLogin = false
        _state.update {
            it.copy(
                session = next,
                account = account,
                statement = statement,
                errorMessage = null,
                selectedTab = tab,
                lastSeen = Instant.now(),
                lastTaxId = next.taxId,
            )
        }
        viewModelScope.launch { prefs.setLastTaxId(next.taxId) }
    }
}
