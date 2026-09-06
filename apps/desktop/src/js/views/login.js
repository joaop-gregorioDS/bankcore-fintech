// Login View
import { CONFIG } from '../config.js';
import { api } from '../api.js';
import { setSecureItem } from '../store.js';

export function renderLogin(container, onLoginSuccess, showToast) {
  container.innerHTML = `
    <div class="login-wrapper">
      <div class="login-card">
        <div class="login-brand-shield">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>

        <h1 class="login-title">
          <span class="bank">Bank</span><span class="core" style="color:var(--accent-gold);">Core</span>
        </h1>
        <p class="login-subtitle">Web Banking Corporativo & Ledger de Partidas Dobradas</p>

        <div style="margin-bottom: 20px;">
          <span class="badge-simulado" style="background-color:var(--accent-gold-soft); padding: 4px 12px; font-size: 10px;">
            Portfólio / Laboratório de Demonstração
          </span>
        </div>

        <div class="form-label" style="text-align: left; margin-bottom: 8px;">Contas de um clique:</div>
        <div class="demo-chips-grid">
          <div class="demo-chip" id="chipLucas">
            <div class="chip-avatar">LM</div>
            <div class="chip-info">
              <span class="chip-name">Lucas Mendes</span>
              <span class="chip-role">PJ · Carbon Black</span>
            </div>
          </div>
          <div class="demo-chip" id="chipMaria">
            <div class="chip-avatar">MS</div>
            <div class="chip-info">
              <span class="chip-name">Maria Silva</span>
              <span class="chip-role">PF · Platinum</span>
            </div>
          </div>
        </div>

        <div class="login-divider">ou credenciais manuais</div>

        <form id="loginForm" style="text-align: left;">
          <div class="form-group">
            <label class="form-label" for="loginTaxId">CPF do Titular</label>
            <input type="text" id="loginTaxId" class="form-input font-mono" placeholder="000.000.000-00" required maxlength="14" autocomplete="username">
          </div>

          <div class="form-group">
            <label class="form-label" for="loginPassword">Senha de Acesso</label>
            <input type="password" id="loginPassword" class="form-input" placeholder="••••••••" required autocomplete="current-password">
          </div>

          <button type="submit" id="btnLoginSubmit" class="btn-gold" style="width: 100%; margin-top: 10px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
              <polyline points="10 17 15 12 10 7"/>
              <line x1="15" y1="12" x2="3" y2="12"/>
            </svg>
            Acessar Conta Segura
          </button>
        </form>

        <div class="login-version-footer">
          version ${CONFIG.appVersion} · ${CONFIG.company.tradeName}
        </div>
      </div>
    </div>
  `;

  const taxIdInput = container.querySelector('#loginTaxId');
  const passwordInput = container.querySelector('#loginPassword');
  const form = container.querySelector('#loginForm');
  const btnSubmit = container.querySelector('#btnLoginSubmit');

  // Format CPF on input
  taxIdInput.addEventListener('input', (e) => {
    let val = e.target.value.replace(/\D/g, '').slice(0, 11);
    if (val.length > 9) val = val.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
    else if (val.length > 6) val = val.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
    else if (val.length > 3) val = val.replace(/(\d{3})(\d{1,3})/, '$1.$2');
    e.target.value = val;
  });

  // Quick fill chips
  container.querySelector('#chipLucas').addEventListener('click', () => {
    taxIdInput.value = '987.654.321-00';
    passwordInput.value = 'teste123456';
    form.dispatchEvent(new Event('submit'));
  });

  container.querySelector('#chipMaria').addEventListener('click', () => {
    taxIdInput.value = '123.456.789-00';
    passwordInput.value = 'teste123456';
    form.dispatchEvent(new Event('submit'));
  });

  // Submit Handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cleanTaxId = taxIdInput.value.replace(/\D/g, '');
    const password = passwordInput.value;

    if (cleanTaxId.length !== 11) {
      showToast('Informe um CPF válido com 11 dígitos.', 'error');
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.innerHTML = `
      <svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
      </svg>
      Autenticando...
    `;

    try {
      const loginRes = await api.login(cleanTaxId, password);
      await setSecureItem('auth_token', loginRes.access_token);

      // Fetch user and account details
      const user = await api.getMe();
      await setSecureItem('auth_user', user);

      const account = await api.getOrCreateAccount(user.id);
      await setSecureItem('auth_account', account);

      showToast(`Bem-vindo(a), ${user.full_name}!`, 'success');
      onLoginSuccess(user, account);
    } catch (err) {
      console.error('Login error:', err);
      showToast(err.message || 'Falha na autenticação. Verifique seu CPF e senha.', 'error');
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = 'Acessar Conta Segura';
    }
  });
}
