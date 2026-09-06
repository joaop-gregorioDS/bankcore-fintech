// Root Application Controller for BankCore Desktop
import { initStore, getSecureItem, setSecureItem, clearAuthSession } from './store.js';
import { CONFIG } from './config.js';
import { renderLogin } from './views/login.js';
import { renderHome } from './views/home.js';
import { renderPix } from './views/pix.js';
import { renderStatement } from './views/statement.js';
import { renderCards } from './views/cards.js';
import { renderHubs } from './views/hubs.js';
import { renderProfile } from './views/profile.js';

class BankCoreDesktopApp {
  constructor() {
    this.user = null;
    this.account = null;
    this.currentTab = 'home';
    this.viewport = document.getElementById('viewport');
    this.sidebar = document.getElementById('desktopSidebar');
    this.contentTopbar = document.getElementById('contentTopbar');
    this.sidebarNav = document.getElementById('sidebarNav');
    this.pageTitleDisplay = document.getElementById('pageTitleDisplay');
    
    // Sidebar User Elements
    this.sidebarAvatar = document.getElementById('sidebarAvatar');
    this.sidebarUserName = document.getElementById('sidebarUserName');
    this.sidebarUserAcc = document.getElementById('sidebarUserAcc');
    this.sidebarUserCard = document.getElementById('sidebarUserCard');
    this.btnQuickLogout = document.getElementById('btnQuickLogout');

    // Topbar Elements
    this.btnToggleThemeTopbar = document.getElementById('btnToggleThemeTopbar');
    this.topbarThemeText = document.getElementById('topbarThemeText');

    this.toastContainer = document.getElementById('toastContainer');
    this.modalContainer = document.getElementById('modalContainer');
  }

  async init() {
    const store = await initStore();

    // Apply stored theme (Light mode by default)
    if (store.theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (this.topbarThemeText) this.topbarThemeText.innerText = 'Escuro';
    } else {
      document.documentElement.removeAttribute('data-theme');
      if (this.topbarThemeText) this.topbarThemeText.innerText = 'Claro';
    }

    // Topbar theme toggle button
    if (this.btnToggleThemeTopbar) {
      this.btnToggleThemeTopbar.addEventListener('click', async () => {
        const isCurrentlyDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const nextTheme = isCurrentlyDark ? 'light' : 'dark';
        await setSecureItem('theme', nextTheme);
        if (nextTheme === 'dark') {
          document.documentElement.setAttribute('data-theme', 'dark');
          if (this.topbarThemeText) this.topbarThemeText.innerText = 'Escuro';
          this.showToast('Modo Escuro ativado.', 'info');
        } else {
          document.documentElement.removeAttribute('data-theme');
          if (this.topbarThemeText) this.topbarThemeText.innerText = 'Claro';
          this.showToast('Modo Claro ativado.', 'info');
        }
      });
    }

    // Handle unauthorized events from API
    window.addEventListener('bankcore:unauthorized', () => {
      this.user = null;
      this.account = null;
      this.showLogin();
      this.showToast('Sessão encerrada por segurança.', 'error');
    });

    // Check existing auth session
    if (store.auth_token && store.auth_user && store.auth_account) {
      this.user = store.auth_user;
      this.account = store.auth_account;
      this.showApp();
    } else {
      this.showLogin();
    }

    // Attach navigation listeners to sidebar buttons
    if (this.sidebarNav) {
      this.sidebarNav.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.getAttribute('data-tab');
          this.navigateTo(tab);
        });
      });
    }

    // Sidebar footer: click user info to go to Profile
    if (this.sidebarUserCard) {
      this.sidebarUserCard.addEventListener('click', (e) => {
        if (e.target.closest('#btnQuickLogout')) return;
        this.navigateTo('profile');
      });
    }

    // Quick logout in sidebar
    if (this.btnQuickLogout) {
      this.btnQuickLogout.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm('Deseja realmente encerrar a sessão corporativa?')) {
          await clearAuthSession();
          this.user = null;
          this.account = null;
          this.showToast('Sessão encerrada.', 'info');
          this.showLogin();
        }
      });
    }
  }

  showLogin() {
    this.sidebar.classList.add('hidden');
    this.contentTopbar.classList.add('hidden');
    renderLogin(this.viewport, (user, account) => {
      this.user = user;
      this.account = account;
      this.showApp();
    }, this.showToast.bind(this));
  }

  showApp() {
    this.sidebar.classList.remove('hidden');
    this.contentTopbar.classList.remove('hidden');
    
    // Update sidebar profile card
    const initials = this.user.full_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
    if (this.sidebarAvatar) this.sidebarAvatar.innerText = initials;
    if (this.sidebarUserName) this.sidebarUserName.innerText = this.user.full_name;
    if (this.sidebarUserAcc) this.sidebarUserAcc.innerText = `Ag. 0001-9 · Cc. ${this.account.account_number}`;

    this.navigateTo('home');
  }

  navigateTo(tab, param = null) {
    this.currentTab = tab;

    // Highlight sidebar active item
    if (this.sidebarNav) {
      this.sidebarNav.querySelectorAll('.nav-item').forEach(btn => {
        if (btn.getAttribute('data-tab') === tab) btn.classList.add('active');
        else btn.classList.remove('active');
      });
    }

    // Update topbar title
    const titles = {
      home: 'Início · Dashboard Geral',
      pix: 'Área Pix · Transferência Instantânea',
      statement: 'Extrato Consolidado & Auditoria Contábil',
      cards: 'Gestão de Cartões Corporativos',
      dda: 'DDA · Boletos Registrados (CIP)',
      invest: 'Carteira de Investimentos',
      credit: 'Crédito & Financiamento (Tabela Price)',
      profile: 'Perfil Corporativo & Configurações',
    };

    if (this.pageTitleDisplay) {
      this.pageTitleDisplay.innerHTML = `<span>${titles[tab] || 'BankCore'}</span>`;
    }

    this.viewport.scrollTop = 0;

    switch (tab) {
      case 'home':
        renderHome(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), this.showReceiptModal.bind(this));
        break;
      case 'pix':
        renderPix(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), this.showReceiptModal.bind(this));
        break;
      case 'statement':
        renderStatement(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), this.showReceiptModal.bind(this));
        break;
      case 'cards':
        renderCards(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this));
        break;
      case 'dda':
        renderHubs(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), 'dda');
        break;
      case 'invest':
        renderHubs(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), 'invest');
        break;
      case 'credit':
        renderHubs(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), 'credit');
        break;
      case 'profile':
        renderProfile(this.viewport, this.user, this.account, () => this.showLogin(), this.showToast.bind(this));
        break;
      default:
        renderHome(this.viewport, this.user, this.account, this.navigateTo.bind(this), this.showToast.bind(this), this.showReceiptModal.bind(this));
    }
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  showReceiptModal(tx, user, account) {
    const date = new Date(tx.created_at || Date.now());
    const dateFormatted = date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
    const timeFormatted = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const authCode = tx.idempotency_key ? `AUT-${tx.idempotency_key.toUpperCase()}` : `AUT-${(tx.transaction_id || 'DEMO').slice(0, 16).toUpperCase()}`;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content" style="max-width: 480px;">
        <div class="modal-header">
          <span style="font-size:13px; font-weight:800; color:var(--accent-gold);">Comprovante Oficial</span>
          <button class="modal-close" id="btnCloseReceipt">✕</button>
        </div>

        <div class="receipt-paper" id="receiptPaperPrint">
          <div class="receipt-header">
            <h3 style="font-size: 18px; font-weight: 900; margin-bottom: 2px;">BankCore</h3>
            <p style="font-size: 11px; color: #6C665A;">Comprovante de Transferência Pix · Ledger Interno</p>
          </div>

          <div style="text-align: center; margin: 16px 0;">
            <span style="font-size: 11px; text-transform: uppercase; color: #6C665A; font-weight: 700;">Valor Transferido</span>
            <div style="font-size: 28px; font-weight: 900; color: #121212; margin-top: 4px;" class="tabular-nums">
              ${Number(tx.amount_reais).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </div>
            <span class="badge-verified" style="margin-top: 6px;">Liquidado com Sucesso</span>
          </div>

          <div class="receipt-row">
            <span class="label">Pagador / Origem:</span>
            <span class="val">${user.full_name}</span>
          </div>
          <div class="receipt-row">
            <span class="label">CPF Origem:</span>
            <span class="val font-mono">${user.tax_id.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')}</span>
          </div>
          <div class="receipt-row">
            <span class="label">Conta Origem:</span>
            <span class="val font-mono">Ag. 0001-9 · Cc. ${account.account_number}</span>
          </div>
          <div class="receipt-row">
            <span class="label">Instituição:</span>
            <span class="val">Banco Vortex S.A.</span>
          </div>
          <div class="receipt-row" style="margin-top:8px; border-top:1px dashed #D0C9B6; padding-top:8px;">
            <span class="label">Destinatário:</span>
            <span class="val">${tx.recipient_name || 'Correntista BankCore'}</span>
          </div>
          <div class="receipt-row">
            <span class="label">Data / Hora:</span>
            <span class="val">${dateFormatted} às ${timeFormatted}</span>
          </div>
          <div class="receipt-row">
            <span class="label">Descrição:</span>
            <span class="val">${tx.description || 'Transferência Pix'}</span>
          </div>

          <div class="receipt-auth-box">
            <div>CÓDIGO DE AUTENTICAÇÃO MECÂNICA</div>
            <strong>${authCode}</strong>
          </div>

          <p style="font-size: 9.5px; text-align: center; color: #8A8476; margin-top: 10px;">
            Documento emitido por sistema de demonstração corporativa. Ledger de partidas dobradas interno (não integrado ao SPI do Banco Central).
          </p>
        </div>

        <div style="display:flex; gap:10px; margin-top:20px;">
          <button id="btnPrintReceipt" class="btn-gold" style="flex:1;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 6 2 18 2 18 9"/>
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
              <rect x="6" y="14" width="12" height="8"/>
            </svg>
            Imprimir / Salvar PDF
          </button>
          <button id="btnDismissReceipt" class="btn-secondary" style="flex:1;">
            Fechar
          </button>
        </div>
      </div>
    `;

    this.modalContainer.appendChild(modal);

    modal.querySelector('#btnCloseReceipt').addEventListener('click', () => modal.remove());
    modal.querySelector('#btnDismissReceipt').addEventListener('click', () => modal.remove());
    modal.querySelector('#btnPrintReceipt').addEventListener('click', () => {
      window.print();
    });
  }
}

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
  const app = new BankCoreDesktopApp();
  app.init();
});
