// Hubs View: DDA Boletos, Investimentos e Crédito (Tabela Price)
import { getMockCatalog } from '../mock.js';

export function renderHubs(container, user, account, onNavigate, showToast, initialSubTab = 'dda') {
  const mockData = getMockCatalog(user.tax_id);

  const formatBRL = (val) => {
    return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  container.innerHTML = `
    <div class="view-container">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px;">
        <div>
          <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Serviços & Operações</h2>
          <p style="font-size:12.5px; color:var(--text-secondary);">Agendamento de boletos, carteira de investimentos e linha de crédito</p>
        </div>
        <span class="badge-simulado">Módulos Simulados</span>
      </div>

      <!-- Sub Tabs -->
      <div style="display:flex; gap:10px; margin-bottom:24px; border-bottom:1px solid var(--border-subtle); padding-bottom:12px;">
        <button class="hub-tab-btn btn-secondary ${initialSubTab === 'dda' ? 'active btn-gold' : ''}" data-hub="dda">
          DDA & Boletos (${mockData.dda.length})
        </button>
        <button class="hub-tab-btn btn-secondary ${initialSubTab === 'invest' ? 'active btn-gold' : ''}" data-hub="invest">
          Investimentos (${formatBRL(mockData.investments.totalReais)})
        </button>
        <button class="hub-tab-btn btn-secondary ${initialSubTab === 'credit' ? 'active btn-gold' : ''}" data-hub="credit">
          Crédito & Financiamento (Tabela Price)
        </button>
      </div>

      <!-- Hub Content Area -->
      <div id="hubContent"></div>
    </div>
  `;

  const hubContent = container.querySelector('#hubContent');

  const renderDDA = () => {
    hubContent.innerHTML = `
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px;">
          <div>
            <h3 style="font-size:16px; font-weight:900;">Débito Direto Autorizado (DDA)</h3>
            <p style="font-size:12px; color:var(--text-secondary);">Boletos registrados no seu CNPJ/CPF pela rede bancária CIP</p>
          </div>
          <strong style="font-size:16px; font-weight:900; color:var(--color-debit);" class="tabular-nums">
            Total: ${formatBRL(mockData.scheduledTotalReais)}
          </strong>
        </div>

        <div style="display:flex; flex-direction:column; gap:12px;">
          ${mockData.dda.map(item => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:14px 18px; background-color:var(--bg-card-subtle); border:1px solid var(--border-subtle); border-radius:var(--radius-md);">
              <div>
                <h4 style="font-size:13.5px; font-weight:800; color:var(--text-primary); margin-bottom:2px;">${item.company}</h4>
                <div style="font-family:var(--font-mono); font-size:11px; color:var(--text-mute); margin-bottom:4px;">${item.barcode}</div>
                <span style="font-size:11px; font-weight:700; color:var(--accent-gold);">Vence em: ${item.due}</span>
              </div>
              <div style="text-align:right;">
                <div style="font-size:16px; font-weight:900; color:var(--text-primary); margin-bottom:6px;" class="tabular-nums">${formatBRL(item.amount)}</div>
                <button class="btn-gold btn-pay-dda" data-company="${item.company}" data-amount="${item.amount}" style="padding:6px 14px; font-size:11.5px;">
                  Pagar Boleto
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    hubContent.querySelectorAll('.btn-pay-dda').forEach(btn => {
      btn.addEventListener('click', () => {
        const comp = btn.getAttribute('data-company');
        const amt = btn.getAttribute('data-amount');
        showToast(`Simulação: Boleto de ${comp} (${formatBRL(amt)}) agendado com sucesso!`, 'info');
      });
    });
  };

  const renderInvest = () => {
    hubContent.innerHTML = `
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px;">
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
            <div>
              <span style="font-size:12px; font-weight:700; color:var(--text-secondary);">Patrimônio Aplicado</span>
              <div style="font-size:28px; font-weight:900; color:var(--text-primary); margin:6px 0;" class="tabular-nums">
                ${formatBRL(mockData.investments.totalReais)}
              </div>
            </div>
            <span class="badge-verified">${mockData.investments.monthlyYield} este mês</span>
          </div>

          <div style="display:flex; flex-direction:column; gap:12px; margin-top:20px;">
            ${mockData.investments.items.map(inv => `
              <div style="padding:14px; background-color:var(--bg-card-subtle); border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                  <strong style="font-size:13px;">${inv.name}</strong>
                  <span style="font-weight:900; color:var(--color-credit);" class="tabular-nums">${formatBRL(inv.value)}</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-mute);">
                  <span>Emissor: ${inv.institution}</span>
                  <span>Liquidez: ${inv.maturity}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="card">
          <h3 style="font-size:16px; font-weight:900; margin-bottom:6px;">Nova Aplicação</h3>
          <p style="font-size:12px; color:var(--text-secondary); margin-bottom:20px;">Produtos com garantia FGC até R$ 250 mil por emissor.</p>

          <div class="form-group">
            <label class="form-label">Produto Selecionado</label>
            <select class="form-input">
              <option>CDB Carbon Liquidez Diária (108% CDI)</option>
              <option>LCI Vortex Verde Sustentável (94% CDI Isento)</option>
              <option>Tesouro Selic 2029 (Taxa Zero)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Valor do Aporte (R$)</label>
            <input type="number" class="form-input" value="1000.00" min="100" step="100">
          </div>

          <button class="btn-gold" style="width:100%; margin-top:10px;" onclick="alert('Simulação: Ordem de investimento enviada à custódia!')">
            Confirmar Aplicação
          </button>
        </div>
      </div>
    `;
  };

  const renderCredit = () => {
    const preApproved = mockData.credit.preApprovedReais;
    hubContent.innerHTML = `
      <div class="card" style="max-width:680px; margin:0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px;">
          <div>
            <h3 style="font-size:18px; font-weight:900;">Simulador de Crédito Corporativo</h3>
            <p style="font-size:12px; color:var(--text-secondary);">Amortização pelo Sistema Francês (Tabela Price) com parcelas fixas</p>
          </div>
          <span class="badge-verified">Pré-aprovado</span>
        </div>

        <div style="background-color:var(--bg-card-subtle); padding:16px; border-radius:var(--radius-md); margin-bottom:24px; border:1px solid var(--border-subtle);">
          <div style="font-size:11.5px; font-weight:700; color:var(--text-mute);">Limite Pré-Aprovado Disponível</div>
          <div style="font-size:24px; font-weight:900; color:var(--accent-gold);" class="tabular-nums">${formatBRL(preApproved)}</div>
          <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Taxa diferenciada Carbon: ${mockData.credit.monthlyRate}</div>
        </div>

        <div class="form-group">
          <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <label class="form-label">Valor do Empréstimo:</label>
            <strong id="creditValLabel" class="tabular-nums">${formatBRL(10000)}</strong>
          </div>
          <input type="range" id="creditRangeVal" min="1000" max="${preApproved}" step="1000" value="10000" style="width:100%; accent-color:var(--accent-gold);">
        </div>

        <div class="form-group" style="margin-top:16px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <label class="form-label">Prazo de Pagamento:</label>
            <strong id="creditMonthsLabel">24 meses</strong>
          </div>
          <input type="range" id="creditRangeMonths" min="6" max="${mockData.credit.maxMonths}" step="6" value="24" style="width:100%; accent-color:var(--accent-gold);">
        </div>

        <div style="padding:18px; background-color:var(--bg-card-subtle); border-radius:var(--radius-md); border:1px solid var(--border-subtle); margin:24px 0;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-size:11px; font-weight:700; color:var(--text-mute); text-transform:uppercase;">Valor da Parcela Fixa (Price)</div>
              <div style="font-size:22px; font-weight:900; color:var(--text-primary);" id="creditInstallmentVal" class="tabular-nums">R$ 498,42 / mês</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:11px; color:var(--text-mute);">Total a Pagar</div>
              <strong style="font-size:14px; color:var(--text-secondary);" id="creditTotalVal" class="tabular-nums">R$ 11.962,08</strong>
            </div>
          </div>
        </div>

        <button class="btn-gold" style="width:100%;" onclick="alert('Simulação: Proposta de crédito aprovada!')">
          Contratar Linha de Crédito
        </button>
      </div>
    `;

    const rangeVal = hubContent.querySelector('#creditRangeVal');
    const rangeMonths = hubContent.querySelector('#creditRangeMonths');
    const lblVal = hubContent.querySelector('#creditValLabel');
    const lblMonths = hubContent.querySelector('#creditMonthsLabel');
    const lblInst = hubContent.querySelector('#creditInstallmentVal');
    const lblTotal = hubContent.querySelector('#creditTotalVal');

    const rate = 0.0149; // 1.49% a.m.

    const recalc = () => {
      const p = parseFloat(rangeVal.value);
      const n = parseInt(rangeMonths.value);
      lblVal.innerText = formatBRL(p);
      lblMonths.innerText = `${n} meses`;

      // Price Formula: PMT = P * [ i * (1 + i)^n ] / [ (1 + i)^n - 1 ]
      const pmt = p * ( (rate * Math.pow(1 + rate, n)) / (Math.pow(1 + rate, n) - 1) );
      const total = pmt * n;

      lblInst.innerText = `${formatBRL(pmt)} / mês`;
      lblTotal.innerText = formatBRL(total);
    };

    rangeVal.addEventListener('input', recalc);
    rangeMonths.addEventListener('input', recalc);
    recalc();
  };

  // Sub Tab switching
  container.querySelectorAll('.hub-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.hub-tab-btn').forEach(b => b.classList.remove('active', 'btn-gold'));
      btn.classList.add('active', 'btn-gold');
      const target = btn.getAttribute('data-hub');
      if (target === 'dda') renderDDA();
      else if (target === 'invest') renderInvest();
      else if (target === 'credit') renderCredit();
    });
  });

  if (initialSubTab === 'invest') renderInvest();
  else if (initialSubTab === 'credit') renderCredit();
  else renderDDA();
}
