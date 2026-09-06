package br.vortex.bankcore

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.core.view.WindowCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import br.vortex.bankcore.ui.BankCoreApp
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.theme.BankCoreTheme

class MainActivity : ComponentActivity() {
    private val viewModel: BankCoreViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val state by viewModel.state.collectAsStateWithLifecycle()
            val dark = state.usesDarkAppearance
            WindowCompat.getInsetsController(window, window.decorView).apply {
                isAppearanceLightStatusBars = !dark
                isAppearanceLightNavigationBars = !dark
            }
            BankCoreTheme(darkTheme = dark) {
                BankCoreApp(viewModel)
            }
        }
    }
}
