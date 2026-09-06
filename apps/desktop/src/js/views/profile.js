// Profile View
import { CONFIG } from '../config.js';
import { getMockCatalog } from '../mock.js';
import { getSecureItem, setSecureItem, clearAuthSession } from '../store.js';

export async function renderProfile(container, user, account, onLogout, showToast) {
  const mockData = getMockCatalog(user.tax_id);
  const currentTheme = (await getSecureItem('theme')) || 'light';

  const initials = user.full_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
  const cpfFormatted = user.tax_id.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');

  container.innerHTML = `
    <div class="view-container">
      <div style="margin-bottom: 24px;">
        <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Perfil & Configurações</h2>
        <p style="font-size:12.5px; color:var(--text-secondary);">Dados da conta corporativa, empresa titular e preferências do sistema</p>
      </div>

      <div class="profile-grid">
        <!-- Left Column: User & Company Info -->
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- User Card -->
          <div class="card">
            <div style="display:flex; align-items:center; gap:16px; margin-bottom:20px;">
              <div class="profile-avatar-large">${initials}</div>
              <div>
                <h3 style="font-size:18px; font-weight:900; margin-bottom:2px;">${user.full_name}</h3>
                <span class="badge-verified">Correntista Verificado</span>
                <div style="font-size:11.5px; color:var(--text-mute); margin-top:4px;" class="font-mono">CPF: ${cpfFormatted}</div>
              </div>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px; font-size:12.5px;">
              <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border-subtle);">
                <span style="color:var(--text-secondary);">Agência / Conta:</span>
                <strong class="font-mono">Ag. ${mockData.agency} · Cc. ${account.account_number}</strong>
              </div>
              <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border-subtle);">
                <span style="color:var(--text-secondary);">E-mail Cadastrado:</span>
                <strong>${user.email || mockData.email || CONFIG.company.email}</strong>
              </div>
              <div style="display:flex; justify-content:space-between; padding:8px 0;">
                <span style="color:var(--text-secondary);">Segmento:</span>
                <strong style="color:var(--accent-gold);">${mockData.segment}</strong>
              </div>
            </div>
          </div>

          <!-- Company PJ Card -->
          <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <h4 style="font-size:14px; font-weight:900; color:var(--text-primary);">Dados da Empresa (Pessoa Jurídica)</h4>
              <span class="badge-simulado">Contabilizei Conectada</span>
            </div>
            
            <div style="background-color:var(--bg-card-subtle); padding:14px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); margin-bottom:10px;">
              <div style="font-size:10.5px; text-transform:uppercase; font-weight:700; color:var(--text-mute);">Razão Social Oficial</div>
              <div style="font-size:13.5px; font-weight:900; color:var(--text-primary); margin-top:2px;">${CONFIG.company.legalName}</div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:12px;">
              <div style="background-color:var(--bg-card-subtle); padding:10px 14px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                <span style="font-size:10px; color:var(--text-mute); text-transform:uppercase; font-weight:700;">Nome Fantasia</span>
                <div style="font-weight:900; color:var(--accent-gold); margin-top:2px;">${CONFIG.company.tradeName}</div>
              </div>
              <div style="background-color:var(--bg-card-subtle); padding:10px 14px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                <span style="font-size:10px; color:var(--text-mute); text-transform:uppercase; font-weight:700;">CNPJ Oficial</span>
                <div style="font-weight:900; font-family:var(--font-mono); margin-top:2px;">${CONFIG.company.cnpj}</div>
              </div>
            </div>
          </div>

          <!-- Compliance & Banking Governance Card -->
          <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h4 style="font-size:13.5px; font-weight:900; color:var(--text-primary);">Conformidade & Governança</h4>
              <span class="badge-verified">Auditoria OK</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px; font-size:11.5px; color:var(--text-secondary);">
              <div style="display:flex; justify-content:space-between;">
                <span>Regime Tributário:</span>
                <strong style="color:var(--text-primary);">Simples Nacional</strong>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span>Segurança Cibernética:</span>
                <strong style="color:var(--color-credit);">BACEN Res. 4.658</strong>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span>Domicílio Bancário:</span>
                <strong style="color:var(--text-primary);">Matriz Curitiba / PR</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Settings & App Info -->
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- System Preferences Card -->
          <div class="card">
            <h4 style="font-size:14px; font-weight:900; margin-bottom:16px;">Preferências do Aplicativo</h4>

            <!-- Theme Toggle -->
            <div class="theme-toggle-container" style="margin-bottom:16px;">
              <div>
                <strong style="font-size:13px;">Aparência Visual</strong>
                <p style="font-size:11.5px; color:var(--text-secondary);" id="themeStatusText">
                  Modo Atual: ${currentTheme === 'dark' ? 'Modo Escuro (Dark)' : 'Modo Claro (Padrão)'}
                </p>
              </div>
              <label class="switch">
                <input type="checkbox" id="themeSwitch" ${currentTheme === 'dark' ? 'checked' : ''}>
                <span class="slider"></span>
              </label>
            </div>

          </div>

          <!-- About App Card -->
          <div class="card">
            <h4 style="font-size:14px; font-weight:900; margin-bottom:14px;">Sobre o Aplicativo</h4>
            <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
              <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Versão do Pacote:</span>
                <strong class="font-mono">version ${CONFIG.appVersion}</strong>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Identificador:</span>
                <strong class="font-mono">br.vortex.bankcore</strong>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Tecnologia:</span>
                <span>Tauri 2 · Rust · WebView2</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Segurança de Dados:</span>
                <span>Tauri Store Vault (Criptografado)</span>
              </div>
            </div>

            <!-- Sair do App Button -->
            <button id="btnLogout" class="btn-debit" style="width:100%; margin-top:24px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Sair da Conta (Encerrar Sessão)
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Theme Switch Handler
  const themeSwitch = container.querySelector('#themeSwitch');
  const themeText = container.querySelector('#themeStatusText');
  themeSwitch.addEventListener('change', async (e) => {
    const isDark = e.target.checked;
    const newTheme = isDark ? 'dark' : 'light';
    await setSecureItem('theme', newTheme);
    if (isDark) {
      document.documentElement.setAttribute('data-theme', 'dark');
      themeText.innerText = 'Modo Atual: Modo Escuro (Dark)';
    } else {
      document.documentElement.removeAttribute('data-theme');
      themeText.innerText = 'Modo Atual: Modo Claro (Padrão)';
    }
    showToast(`Tema alterado para ${isDark ? 'Escuro' : 'Claro'}.`, 'info');
  });

  // Logout Handler
  container.querySelector('#btnLogout').addEventListener('click', async () => {
    if (confirm('Deseja realmente sair da sua conta no BankCore?')) {
      await clearAuthSession();
      showToast('Sessão encerrada com sucesso.', 'info');
      onLogout();
    }
  });
}
