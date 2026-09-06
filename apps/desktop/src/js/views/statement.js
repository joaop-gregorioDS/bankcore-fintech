// Statement View
import { api } from '../api.js';

export async function renderStatement(container, user, account, onNavigate, showToast, showReceiptModal) {
  const formatBRL = (val) => {
    return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  container.innerHTML = `
    <div class="view-container">
      <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 24px;">
        <div>
          <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Extrato Consolidado</h2>
          <p style="font-size:12.5px; color:var(--text-secondary);">Trilha de auditoria contábil com partidas dobradas e liquidação em tempo real</p>
        </div>

        <div style="display:flex; gap:10px;">
          <button id="btnDepositDemo" class="btn-secondary" style="font-size:12px; padding:8px 14px;">
            + Depósito Demo (R$ 500,00)
          </button>
          <button id="btnRefreshStatement" class="btn-secondary" style="font-size:12px; padding:8px 12px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Filter Tabs -->
      <div style="display:flex; gap:8px; margin-bottom:20px;">
        <button class="filter-tab active btn-secondary" data-filter="all" style="padding:6px 16px; font-size:12px;">Todos</button>
        <button class="filter-tab btn-secondary" data-filter="credit" style="padding:6px 16px; font-size:12px;">Entradas (+)</button>
        <button class="filter-tab btn-secondary" data-filter="debit" style="padding:6px 16px; font-size:12px;">Saídas (-)</button>
      </div>

      <!-- Transactions Container -->
      <div class="card" style="padding:12px;" id="statementList">
        <p style="padding:20px; text-align:center; color:var(--text-mute);">Carregando lançamentos...</p>
      </div>
    </div>
  `;

  let currentFilter = 'all';
  let cachedTxs = [];

  const listContainer = container.querySelector('#statementList');

  const renderList = () => {
    let filtered = cachedTxs;
    if (currentFilter === 'credit') filtered = cachedTxs.filter(t => t.direction === 'CREDIT');
    if (currentFilter === 'debit') filtered = cachedTxs.filter(t => t.direction === 'DEBIT');

    if (filtered.length === 0) {
      listContainer.innerHTML = `
        <div style="padding:40px 20px; text-align:center; color:var(--text-mute);">
          <p style="font-size:14px; font-weight:700;">Nenhuma movimentação encontrada para o filtro selecionado.</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = filtered.map(tx => {
      const isCredit = tx.direction === 'CREDIT';
      const date = new Date(tx.created_at);
      const dateFormatted = date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
      const timeFormatted = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

      return `
        <div class="tx-item" data-tx-id="${tx.transaction_id}">
          <div class="tx-info">
            <div class="tx-icon ${isCredit ? 'tx-credit' : 'tx-debit'}">
              ${isCredit ? '↓' : '↑'}
            </div>
            <div class="tx-details">
              <h4>${tx.description || (isCredit ? 'Recebimento Pix' : 'Envio Pix')}</h4>
              <p>${dateFormatted} às ${timeFormatted} · <span style="font-family:var(--font-mono); font-size:10px;">ID: ${tx.transaction_id.slice(0, 8)}</span></p>
            </div>
          </div>
          <div style="text-align:right;">
            <div class="tx-value ${isCredit ? 'credit' : 'debit'} tabular-nums">
              ${isCredit ? '+' : '-'} ${formatBRL(tx.amount_reais)}
            </div>
            <span style="font-size:10.5px; color:var(--text-mute);">${tx.status} · Ver Comprovante</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners to open receipt
    listContainer.querySelectorAll('.tx-item').forEach(item => {
      item.addEventListener('click', () => {
        const txId = item.getAttribute('data-tx-id');
        const found = cachedTxs.find(t => t.transaction_id === txId);
        if (found) showReceiptModal(found, user, account);
      });
    });
  };

  const fetchTxs = async () => {
    try {
      cachedTxs = await api.getStatement(account.id);
      renderList();
    } catch (err) {
      listContainer.innerHTML = `<p style="padding:20px; text-align:center; color:var(--color-debit);">Falha ao carregar extrato: ${err.message}</p>`;
    }
  };

  // Filter tab clicks
  container.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active', 'btn-gold'));
      tab.classList.add('active');
      currentFilter = tab.getAttribute('data-filter');
      renderList();
    });
  });

  // Refresh
  container.querySelector('#btnRefreshStatement').addEventListener('click', () => {
    showToast('Atualizando extrato...', 'info');
    fetchTxs();
  });

  // Deposit demo button
  container.querySelector('#btnDepositDemo').addEventListener('click', async () => {
    try {
      await api.deposit(account.id, 500);
      account.balance_reais += 500;
      showToast('Depósito de R$ 500,00 liquidado no ledger!', 'success');
      fetchTxs();
    } catch (e) {
      showToast('Falha no depósito demo.', 'error');
    }
  });

  await fetchTxs();
}
