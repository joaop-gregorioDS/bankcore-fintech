// Pix View (2-Column Corporate Desktop Grid)
import { api } from '../api.js';

export function renderPix(container, user, account, onNavigate, showToast, showReceiptModal) {
  const isLucas = user.tax_id.replace(/\D/g, '') === '98765432100';
  const defaultTargetCpf = isLucas ? '123.456.789-00' : '987.654.321-00';
  const defaultTargetName = isLucas ? 'Maria Silva Santos' : 'Lucas Mendes Rocha';
  const userCpfFormatted = user.tax_id.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');

  container.innerHTML = `
    <div class="view-container">
      <div style="margin-bottom: 22px;">
        <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Área Pix</h2>
        <p style="font-size:12.5px; color:var(--text-secondary);">Transferência instantânea corporativa com liquidação em tempo real no ledger de partidas dobradas</p>
      </div>

      <div class="pix-desktop-grid">
        <!-- Left Column: Pix Transfer Form -->
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid var(--border-subtle);">
            <div>
              <span style="font-size:11.5px; font-weight:700; color:var(--text-secondary);">Saldo Disponível para Pix</span>
              <div style="font-size:20px; font-weight:900; color:var(--accent-gold);" class="tabular-nums">
                ${Number(account.balance_reais).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </div>
            </div>
            <span class="badge-verified">Liquidação Instantânea</span>
          </div>

          <form id="pixForm">
            <!-- Destination CPF -->
            <div class="form-group">
              <label class="form-label" for="pixDestinationCpf">Chave Pix (CPF do Destinatário)</label>
              <div style="position:relative;">
                <input type="text" id="pixDestinationCpf" class="form-input font-mono" placeholder="000.000.000-00" required maxlength="14" value="${defaultTargetCpf}">
                <button type="button" id="btnQuickFillTarget" class="btn-secondary" style="position:absolute; right:6px; top:6px; padding:6px 12px; font-size:11px;">
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
            <button type="submit" id="btnSubmitPix" class="btn-gold" style="width:100%; margin-top:14px; font-size:14px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                <line x1="4" y1="22" x2="4" y2="15"/>
              </svg>
              Confirmar e Transferir Pix
            </button>
          </form>
        </div>

        <!-- Right Column: My Keys & Operational Limits & Security -->
        <div class="pix-side-col">
          <!-- Card 1: My Registered Pix Key -->
          <div class="pix-key-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h3 style="font-size:14px; font-weight:900; color:var(--text-primary);">Sua Chave Pix Vinculada</h3>
              <span class="badge-verified">DICT Ativo</span>
            </div>

            <p style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">
              Compartilhe sua chave oficial para receber transferências instantâneas nesta conta.
            </p>

            <div class="pix-key-display">
              <div>
                <span style="font-size:10px; text-transform:uppercase; font-weight:700; color:var(--text-mute);">CPF / Chave Primária</span>
                <div style="font-size:14px; font-weight:900; color:var(--text-primary); margin-top:2px;" class="font-mono" id="myPixKeyText">
                  ${userCpfFormatted}
                </div>
              </div>
              <button type="button" id="btnCopyMyPixKey" class="btn-secondary" style="padding:6px 12px; font-size:11px;" title="Copiar Chave Pix">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                <span>Copiar</span>
              </button>
            </div>

            <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-mute);">
              <span>Titular: <strong>${user.full_name}</strong></span>
              <span>Instituição: <strong>Banco Vortex S.A.</strong></span>
            </div>
          </div>

          <!-- Card 2: Limits & Governance -->
          <div class="pix-key-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h3 style="font-size:14px; font-weight:900; color:var(--text-primary);">Limites Operacionais Pix</h3>
              <span class="badge-simulado">Gestão BACEN</span>
            </div>

            <div style="margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
                <span style="color:var(--text-secondary);">Limite Diário (06h às 20h)</span>
                <strong style="color:var(--text-primary);">R$ 50.000,00</strong>
              </div>
              <div style="height:6px; background-color:var(--border-subtle); border-radius:4px; overflow:hidden;">
                <div style="width: 8%; height:100%; background-color:var(--color-credit);"></div>
              </div>
              <div style="display:flex; justify-content:space-between; font-size:10.5px; color:var(--text-mute); margin-top:4px;">
                <span>Disponível: R$ 49.000,00</span>
                <span>Utilizado hoje: R$ 1.000,00</span>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; padding:10px 14px; background-color:var(--bg-card-subtle); border-radius:var(--radius-md); border:1px solid var(--border-subtle); margin-bottom:14px;">
              <div>
                <span style="font-size:10px; color:var(--text-mute); text-transform:uppercase; font-weight:700;">Limite Noturno (20h às 06h)</span>
                <div style="font-size:13px; font-weight:900; color:var(--text-primary); margin-top:2px;">R$ 5.000,00</div>
              </div>
              <span class="badge-verified" style="align-self:center;">Ativo</span>
            </div>

            <!-- Ledger Guarantee Note -->
            <div style="display:flex; gap:10px; align-items:flex-start; padding:12px; background:var(--accent-gold-soft); border-radius:var(--radius-md); border:1px solid var(--accent-gold-border);">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color:var(--accent-gold); flex-shrink:0; margin-top:2px;">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <p style="font-size:11px; color:var(--text-secondary); line-height:1.4;">
                <strong>Garantia de Partidas Dobradas:</strong> Toda movimentação é liquidada com idempotência exclusiva e trilha auditável gravada em banco relacional PostgreSQL.
              </p>
            </div>
          </div>
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

  // Copy own Pix key
  const btnCopy = container.querySelector('#btnCopyMyPixKey');
  if (btnCopy) {
    btnCopy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(user.tax_id.replace(/\D/g, ''));
        showToast('Chave Pix (CPF) copiada para a área de transferência!', 'success');
      } catch {
        showToast(`Chave Pix: ${userCpfFormatted}`, 'info');
      }
    });
  }

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
