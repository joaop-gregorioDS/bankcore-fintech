// Pix View
import { api } from '../api.js';

export function renderPix(container, user, account, onNavigate, showToast, showReceiptModal) {
  const isLucas = user.tax_id.replace(/\D/g, '') === '98765432100';
  const defaultTargetCpf = isLucas ? '123.456.789-00' : '987.654.321-00';
  const defaultTargetName = isLucas ? 'Maria Silva Santos' : 'Lucas Mendes Rocha';

  container.innerHTML = `
    <div class="view-container">
      <div class="pix-container">
        <div style="margin-bottom: 24px;">
          <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Área Pix</h2>
          <p style="font-size:12.5px; color:var(--text-secondary);">Transferência instantânea entre correntistas com liquidação no ledger</p>
        </div>

        <div class="card" style="margin-bottom: 24px;">
          <form id="pixForm">
            <!-- Source Account Balance -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid var(--border-subtle);">
              <span style="font-size:12px; font-weight:700; color:var(--text-secondary);">Saldo Disponível para Pix</span>
              <strong style="font-size:16px; font-weight:900; color:var(--accent-gold);" class="tabular-nums">
                ${Number(account.balance_reais).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </strong>
            </div>

            <!-- Destination CPF -->
            <div class="form-group">
              <label class="form-label" for="pixDestinationCpf">Chave Pix (CPF do Destinatário)</label>
              <div style="position:relative;">
                <input type="text" id="pixDestinationCpf" class="form-input font-mono" placeholder="000.000.000-00" required maxlength="14" value="${defaultTargetCpf}">
                <button type="button" id="btnQuickFillTarget" class="btn-secondary" style="position:absolute; right:6px; top:6px; padding:6px 10px; font-size:11px;">
                  Destino Demo (${isLucas ? 'Maria' : 'Lucas'})
                </button>
              </div>
            </div>

            <!-- Recipient Preview Box -->
            <div id="recipientBox" class="recipient-card">
              <div>
                <div style="font-size:10.5px; text-transform:uppercase; font-weight:800; color:var(--text-mute);">Destinatário Identificado</div>
                <div style="font-size:14px; font-weight:900; color:var(--text-primary);" id="recipientNameText">${defaultTargetName}</div>
                <div style="font-size:11.5px; color:var(--text-secondary);" id="recipientBankText">Banco Vortex S.A. · Agência 0001-9</div>
              </div>
              <span class="badge-verified">Diretório DICT</span>
            </div>

            <!-- Amount Input -->
            <div class="form-group">
              <label class="form-label" for="pixAmount">Valor da Transferência (R$)</label>
              <input type="number" id="pixAmount" class="form-input tabular-nums" style="font-size:20px; font-weight:900;" placeholder="0,00" min="0.01" step="0.01" value="1.00" required>
              
              <div class="quick-amounts">
                <button type="button" class="amount-chip" data-add="1">+ R$ 1,00</button>
                <button type="button" class="amount-chip" data-add="10">+ R$ 10,00</button>
                <button type="button" class="amount-chip" data-add="50">+ R$ 50,00</button>
                <button type="button" class="amount-chip" data-add="100">+ R$ 100,00</button>
              </div>
            </div>

            <!-- Description -->
            <div class="form-group">
              <label class="form-label" for="pixDescription">Descrição ou Mensagem (Opcional)</label>
              <input type="text" id="pixDescription" class="form-input" placeholder="Ex: Pagamento de serviços ou Pix teste" value="Pix BankCore Desktop">
            </div>

            <!-- Submit CTA -->
            <button type="submit" id="btnSubmitPix" class="btn-gold" style="width:100%; margin-top:12px; font-size:14px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                <line x1="4" y1="22" x2="4" y2="15"/>
              </svg>
              Confirmar e Transferir Pix
            </button>
          </form>
        </div>
      </div>
    </div>
  `;

  const inputCpf = container.querySelector('#pixDestinationCpf');
  const inputAmount = container.querySelector('#pixAmount');
  const inputDesc = container.querySelector('#pixDescription');
  const form = container.querySelector('#pixForm');
  const btnSubmit = container.querySelector('#btnSubmitPix');
  const recipientName = container.querySelector('#recipientNameText');

  // CPF Mask & Live Directory Lookup
  let lookupDebounce = null;
  const triggerLookup = () => {
    const clean = inputCpf.value.replace(/\D/g, '');
    if (clean.length === 11) {
      clearTimeout(lookupDebounce);
      lookupDebounce = setTimeout(async () => {
        try {
          const found = await api.lookupDirectory(clean);
          recipientName.innerText = found.full_name || 'Correntista Identificado';
        } catch {
          recipientName.innerText = 'Correntista Não Encontrado';
        }
      }, 300);
    }
  };

  inputCpf.addEventListener('input', (e) => {
    let val = e.target.value.replace(/\D/g, '').slice(0, 11);
    if (val.length > 9) val = val.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
    else if (val.length > 6) val = val.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
    else if (val.length > 3) val = val.replace(/(\d{3})(\d{1,3})/, '$1.$2');
    e.target.value = val;
    triggerLookup();
  });

  // Quick fill demo button
  container.querySelector('#btnQuickFillTarget').addEventListener('click', () => {
    inputCpf.value = defaultTargetCpf;
    recipientName.innerText = defaultTargetName;
    inputAmount.value = '1.00';
  });

  // Quick amount chips
  container.querySelectorAll('.amount-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const add = Number(btn.getAttribute('data-add') || 0);
      const current = Number(inputAmount.value || 0);
      inputAmount.value = (current + add).toFixed(2);
    });
  });

  // Form Submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cleanCpf = inputCpf.value.replace(/\D/g, '');
    const amount = parseFloat(inputAmount.value);
    const desc = inputDesc.value.trim() || 'Pix BankCore Desktop';

    if (cleanCpf.length !== 11) {
      showToast('CPF de destino inválido.', 'error');
      return;
    }
    if (isNaN(amount) || amount <= 0) {
      showToast('Informe um valor maior que R$ 0,00.', 'error');
      return;
    }
    if (amount > account.balance_reais) {
      showToast('Saldo insuficiente em conta corrente.', 'error');
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.innerHTML = 'Liquidando no Ledger...';

    try {
      const res = await api.transferPix(account.id, cleanCpf, amount, desc);
      
      // Update local account balance cache
      account.balance_reais = Math.max(0, account.balance_reais - amount);

      showToast(`Pix de R$ ${amount.toFixed(2)} enviado com sucesso!`, 'success');

      // Open receipt immediately
      showReceiptModal({
        transaction_id: res.transaction_id || `tx_${Date.now()}`,
        idempotency_key: res.idempotency_key,
        amount_reais: amount,
        created_at: new Date().toISOString(),
        direction: 'DEBIT',
        description: desc,
        status: 'COMPLETED',
        recipient_name: recipientName.innerText,
        recipient_cpf: cleanCpf,
      }, user, account);

      // Reset form amount
      inputAmount.value = '1.00';
    } catch (err) {
      console.error('Pix transfer error:', err);
      showToast(err.message || 'Falha ao processar Pix.', 'error');
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = 'Confirmar e Transferir Pix';
    }
  });
}
