// Home View
import { getMockCatalog } from '../mock.js';
import { api } from '../api.js';
import { getSecureItem, setSecureItem } from '../store.js';

export async function renderHome(container, user, account, onNavigate, showToast, showReceiptModal) {
  const mockData = getMockCatalog(user.tax_id);
  let hideBalance = await getSecureItem('hide_balance');

  const formatBRL = (val) => {
    return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  container.innerHTML = `
    <div class="view-container">
      <!-- Header Greeting -->
      <div class="home-header">
        <div class="user-greeting">
          <div class="greeting-avatar">${user.full_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()}</div>
          <div class="greeting-text">
            <h2>Olá, ${user.full_name.split(' ')[0]}</h2>
            <p>${mockData.segment} · Ag. ${mockData.agency} · Cc. ${account.account_number}</p>
          </div>
        </div>

        <div style="display:flex; align-items:center; gap:10px;">
          <button id="btnToggleBalance" class="btn-secondary" style="padding: 8px 14px;" title="Ocultar / Exibir Saldos">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            <span style="font-size:12px;">${hideBalance ? 'Mostrar' : 'Ocultar'}</span>
          </button>
          <button id="btnRefreshBalance" class="btn-secondary" style="padding: 8px 12px;" title="Atualizar dados">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Balance & Scheduled Cards -->
      <div class="balance-card-grid">
        <div class="balance-card">
          <div class="balance-label">
            <span>Saldo em Conta Corrente</span>
            <span class="badge-verified">API Ao Vivo</span>
          </div>
          <div class="balance-amount tabular-nums" id="displayBalance">
            ${hideBalance ? 'R$ ••••••••' : formatBRL(account.balance_reais)}
          </div>
          <div class="balance-footer">
            <span>Rendimento automático CDI: 100%</span>
            <span style="font-family:var(--font-mono); font-size:11px;">Partidas Dobradas Ativas</span>
          </div>
        </div>

        <div class="scheduled-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="font-size:12px; font-weight:700; color:var(--text-secondary);">Agendados (DDA)</div>
            <span class="badge-simulado">Simulado</span>
          </div>
          <div class="scheduled-amount tabular-nums" id="displayScheduled">
            ${hideBalance ? 'R$ ••••••••' : formatBRL(mockData.scheduledTotalReais)}
          </div>
          <div style="font-size:11.5px; color:var(--text-mute);">
            ${mockData.dda.length} boletos a liquidar neste mês
          </div>
        </div>
      </div>

      <!-- 2x4 Quick Action Grid -->
      <div class="quick-actions-grid">
        <button class="quick-action-btn" data-nav="pix">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
              <line x1="4" y1="22" x2="4" y2="15"/>
            </svg>
          </div>
          <span class="action-label">Transferir Pix</span>
        </button>

        <button class="quick-action-btn" data-nav="statement">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <rect x="3" y="4" width="18" height="16" rx="2"/>
              <line x1="7" y1="8" x2="17" y2="8"/>
              <line x1="7" y1="12" x2="17" y2="12"/>
              <line x1="7" y1="16" x2="13" y2="16"/>
            </svg>
          </div>
          <span class="action-label">Extrato</span>
        </button>

        <button class="quick-action-btn" data-nav="dda">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <rect x="2" y="5" width="20" height="14" rx="2"/>
              <line x1="2" y1="10" x2="22" y2="10"/>
            </svg>
          </div>
          <span class="action-label">Pagar DDA</span>
        </button>

        <button class="quick-action-btn" data-nav="invest">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
              <polyline points="17 6 23 6 23 12"/>
            </svg>
          </div>
          <span class="action-label">Investir</span>
        </button>

        <button class="quick-action-btn" data-nav="cards">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
          </div>
          <span class="action-label">Cartões</span>
        </button>

        <button class="quick-action-btn" data-nav="credit">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
              <path d="M12 18V6"/>
            </svg>
          </div>
          <span class="action-label">Empréstimos</span>
        </button>

        <button class="quick-action-btn" data-nav="dda">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <span class="action-label">Boletos</span>
        </button>

        <button class="quick-action-btn" data-nav="profile">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </div>
          <span class="action-label">Ajustes</span>
        </button>
      </div>

      <!-- Dual Split Section: Recent Activity & Cards Preview -->
      <div class="home-dual-sections">
        <!-- Recent Live Ledger Activity -->
        <div class="card">
          <div class="section-title-row">
            <h3 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              Extrato Recente
            </h3>
            <button class="btn-secondary" style="padding: 4px 12px; font-size:11px;" data-nav="statement">
              Ver Completo →
            </button>
          </div>
          <div id="homeRecentTxList">
            <p style="color:var(--text-mute); font-size:12px; padding:12px 0;">Carregando transações do razão...</p>
          </div>
        </div>

        <!-- Cards / Promo Preview -->
        <div class="card">
          <div class="section-title-row">
            <h3 class="section-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <rect x="1" y="4" width="22" height="16" rx="2"/>
                <line x1="1" y1="10" x2="23" y2="10"/>
              </svg>
              Cartão Principal
            </h3>
            <span class="badge-simulado">Simulado</span>
          </div>

          ${mockData.cards[0] ? `
            <div class="card-visual carbon-black" style="max-width:100%; height:190px; padding:20px; margin-bottom:14px; cursor:pointer;" data-nav="cards">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:14px; font-weight:900; letter-spacing:0.5px; color:var(--accent-gold);">${mockData.cards[0].name}</span>
                <span style="font-size:12px; font-weight:800; opacity:0.9;">${mockData.cards[0].brand}</span>
              </div>
              <div class="card-chip-element" style="width:32px; height:24px;"></div>
              <div>
                <div style="font-family:var(--font-mono); font-size:15px; letter-spacing:2px; margin-bottom:4px;">•••• •••• •••• ${mockData.cards[0].last4}</div>
                <div style="display:flex; justify-content:space-between; font-size:11px; opacity:0.8;">
                  <span>${mockData.cards[0].holder}</span>
                  <span>Venc: ${mockData.cards[0].dueDate}</span>
                </div>
              </div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px; padding:0 4px;">
              <span style="color:var(--text-secondary);">Fatura Atual: <strong style="color:var(--text-primary);">${hideBalance ? 'R$ •••••' : formatBRL(mockData.cards[0].invoice)}</strong></span>
              <span style="color:var(--text-secondary);">Disponível: <strong style="color:var(--color-credit);">${hideBalance ? 'R$ •••••' : formatBRL(mockData.cards[0].available)}</strong></span>
            </div>
          ` : '<p style="color:var(--text-mute);">Nenhum cartão cadastrado.</p>'}
        </div>
      </div>
    </div>
  `;

  // Balance Hide/Show Toggle
  const btnToggle = container.querySelector('#btnToggleBalance');
  btnToggle.addEventListener('click', async () => {
    hideBalance = !hideBalance;
    await setSecureItem('hide_balance', hideBalance);
    btnToggle.querySelector('span').innerText = hideBalance ? 'Mostrar' : 'Ocultar';
    container.querySelector('#displayBalance').innerText = hideBalance ? 'R$ ••••••••' : formatBRL(account.balance_reais);
    container.querySelector('#displayScheduled').innerText = hideBalance ? 'R$ ••••••••' : formatBRL(mockData.scheduledTotalReais);
  });

  // Refresh Balance Button
  const btnRefresh = container.querySelector('#btnRefreshBalance');
  btnRefresh.addEventListener('click', async () => {
    btnRefresh.classList.add('animate-spin');
    try {
      const refreshedAcc = await api.getAccount(account.id);
      account.balance_reais = refreshedAcc.balance_reais;
      container.querySelector('#displayBalance').innerText = hideBalance ? 'R$ ••••••••' : formatBRL(refreshedAcc.balance_reais);
      showToast('Saldos atualizados com sucesso.', 'info');
      await loadRecentTransactions();
    } catch (err) {
      showToast('Falha ao atualizar saldo.', 'error');
    } finally {
      btnRefresh.classList.remove('animate-spin');
    }
  });

  // Quick navigation buttons
  container.querySelectorAll('[data-nav]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-nav');
      onNavigate(target);
    });
  });

  // Load Recent Transactions from Live API
  async function loadRecentTransactions() {
    const listEl = container.querySelector('#homeRecentTxList');
    try {
      const txs = await api.getStatement(account.id);
      if (!txs || txs.length === 0) {
        listEl.innerHTML = '<p style="color:var(--text-mute); font-size:12px; padding:12px 0;">Nenhuma transação encontrada.</p>';
        return;
      }

      listEl.innerHTML = txs.slice(0, 4).map(tx => {
        const isCredit = tx.direction === 'CREDIT';
        const dateStr = new Date(tx.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        return `
          <div class="tx-item" data-tx-id="${tx.transaction_id}">
            <div class="tx-info">
              <div class="tx-icon ${isCredit ? 'tx-credit' : 'tx-debit'}">
                ${isCredit ? '↓' : '↑'}
              </div>
              <div class="tx-details">
                <h4>${tx.description || (isCredit ? 'Recebimento Pix' : 'Envio Pix')}</h4>
                <p>${dateStr} · ${tx.status}</p>
              </div>
            </div>
            <div class="tx-value ${isCredit ? 'credit' : 'debit'} tabular-nums">
              ${isCredit ? '+' : '-'} ${formatBRL(tx.amount_reais)}
            </div>
          </div>
        `;
      }).join('');

      // Add click handlers for receipts
      listEl.querySelectorAll('.tx-item').forEach(item => {
        item.addEventListener('click', () => {
          const txId = item.getAttribute('data-tx-id');
          const found = txs.find(t => t.transaction_id === txId);
          if (found) showReceiptModal(found, user, account);
        });
      });
    } catch (err) {
      console.warn('Could not load recent tx:', err);
      listEl.innerHTML = '<p style="color:var(--text-mute); font-size:12px; padding:12px 0;">Sem lançamentos recentes.</p>';
    }
  }

  loadRecentTransactions();
}
