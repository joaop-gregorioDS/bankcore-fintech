// Cards View
import { getMockCatalog } from '../mock.js';

export function renderCards(container, user, account, onNavigate, showToast) {
  const mockData = getMockCatalog(user.tax_id);

  const formatBRL = (val) => {
    return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  container.innerHTML = `
    <div class="view-container">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px;">
        <div>
          <h2 style="font-size:22px; font-weight:900; letter-spacing:-0.5px;">Gestão de Cartões</h2>
          <p style="font-size:12.5px; color:var(--text-secondary);">Controle de limites corporativos, cartões físicos e virtuais</p>
        </div>
        <span class="badge-simulado">Módulo Simulado</span>
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 24px;">
        <!-- Card 1: Physical Card -->
        ${mockData.cards[0] ? `
          <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <span style="font-size:13px; font-weight:800; color:var(--text-primary);">Cartão Físico Principal</span>
              <span class="badge-verified">Ativo</span>
            </div>

            <div class="card-visual carbon-black" style="margin-bottom:20px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:15px; font-weight:900; letter-spacing:0.5px; color:var(--accent-gold);">${mockData.cards[0].name}</span>
                <span style="font-size:13px; font-weight:800;">${mockData.cards[0].brand}</span>
              </div>
              <div class="card-chip-element"></div>
              <div>
                <div style="font-family:var(--font-mono); font-size:16px; letter-spacing:2.5px; margin-bottom:6px;">•••• •••• •••• ${mockData.cards[0].last4}</div>
                <div style="display:flex; justify-content:space-between; font-size:11px; opacity:0.85;">
                  <span>${mockData.cards[0].holder}</span>
                  <span>Vencimento: ${mockData.cards[0].dueDate}</span>
                </div>
              </div>
            </div>

            <div style="margin-bottom:18px;">
              <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
                <span style="color:var(--text-secondary);">Limite Utilizado</span>
                <strong style="color:var(--text-primary);">${formatBRL(mockData.cards[0].used)} de ${formatBRL(mockData.cards[0].total)}</strong>
              </div>
              <div style="height:6px; background-color:var(--border-subtle); border-radius:4px; overflow:hidden;">
                <div style="width: ${(mockData.cards[0].used / mockData.cards[0].total) * 100}%; height:100%; background-color:var(--accent-gold);"></div>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; padding:12px 16px; background-color:var(--bg-card-subtle); border-radius:var(--radius-md); margin-bottom:18px;">
              <div>
                <div style="font-size:10.5px; text-transform:uppercase; font-weight:700; color:var(--text-mute);">Fatura Fechada</div>
                <div style="font-size:16px; font-weight:900; color:var(--color-debit);">${formatBRL(mockData.cards[0].invoice)}</div>
              </div>
              <button class="btn-gold" style="padding:8px 16px; font-size:12px;" onclick="alert('Simulação: Boleto da fatura enviado por e-mail!')">
                Pagar Fatura
              </button>
            </div>

            <div style="display:flex; gap:10px;">
              <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="alert('Simulação: Limite reajustado!')">
                Ajustar Limite
              </button>
              <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="alert('Simulação: Cartão bloqueado com segurança!')">
                Bloquear Cartão
              </button>
            </div>
          </div>
        ` : ''}

        <!-- Card 2: Virtual Card or Platinum -->
        ${mockData.cards[1] ? `
          <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <span style="font-size:13px; font-weight:800; color:var(--text-primary);">Cartão Virtual Seguro</span>
              <span class="badge-verified">Compras Online</span>
            </div>

            <div class="card-visual carbon-virtual" style="margin-bottom:20px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:15px; font-weight:900; letter-spacing:0.5px; color:#38BDF8;">${mockData.cards[1].name}</span>
                <span style="font-size:13px; font-weight:800;">${mockData.cards[1].brand}</span>
              </div>
              <div class="card-chip-element"></div>
              <div>
                <div style="font-family:var(--font-mono); font-size:16px; letter-spacing:2.5px; margin-bottom:6px;">•••• •••• •••• ${mockData.cards[1].last4}</div>
                <div style="display:flex; justify-content:space-between; font-size:11px; opacity:0.85;">
                  <span>${mockData.cards[1].holder}</span>
                  <span>CVV Dinâmico: Ativo</span>
                </div>
              </div>
            </div>

            <div style="margin-bottom:18px;">
              <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
                <span style="color:var(--text-secondary);">Limite Utilizado</span>
                <strong style="color:var(--text-primary);">${formatBRL(mockData.cards[1].used)} de ${formatBRL(mockData.cards[1].total)}</strong>
              </div>
              <div style="height:6px; background-color:var(--border-subtle); border-radius:4px; overflow:hidden;">
                <div style="width: ${(mockData.cards[1].used / mockData.cards[1].total) * 100}%; height:100%; background-color:#38BDF8;"></div>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; padding:12px 16px; background-color:var(--bg-card-subtle); border-radius:var(--radius-md); margin-bottom:18px;">
              <div>
                <div style="font-size:10.5px; text-transform:uppercase; font-weight:700; color:var(--text-mute);">Fatura Virtual</div>
                <div style="font-size:16px; font-weight:900; color:var(--text-primary);">${formatBRL(mockData.cards[1].invoice)}</div>
              </div>
              <span class="badge-simulado" style="align-self:center;">Debitado na Fatura</span>
            </div>

            <div style="display:flex; gap:10px;">
              <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="alert('Simulação: Dados do cartão virtual copiados!')">
                Ver Dados & CVV
              </button>
              <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="alert('Simulação: Novo cartão virtual gerado com sucesso!')">
                Gerar Novo Cartão
              </button>
            </div>
          </div>
        ` : `
          <div class="card" style="display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:40px 20px;">
            <div style="width:50px; height:50px; border-radius:50%; background-color:var(--accent-gold-soft); color:var(--accent-gold); display:flex; align-items:center; justify-content:center; margin-bottom:16px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </div>
            <h3 style="font-size:16px; font-weight:900; margin-bottom:6px;">Criar Cartão Virtual</h3>
            <p style="font-size:12px; color:var(--text-secondary); max-width:280px; margin-bottom:18px;">Gere um cartão virtual temporário ou recorrente com CVV dinâmico para pagamentos corporativos.</p>
            <button class="btn-gold" style="font-size:12px;" onclick="alert('Simulação: Cartão virtual gerado!')">
              Solicitar Cartão Virtual
            </button>
          </div>
        `}
      </div>

      <!-- Corporate Card Benefits & Governance Section -->
      <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px;">
        <div class="card-subtle">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <div style="width:30px; height:30px; border-radius:8px; background:var(--accent-gold-soft); color:var(--accent-gold); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:13px;">
              ✓
            </div>
            <strong style="font-size:13px; color:var(--text-primary);">Conciliação OFX/CSV</strong>
          </div>
          <p style="font-size:11.5px; color:var(--text-secondary); line-height:1.4;">
            Despesas corporativas integradas com a Contabilizei e os principais ERPs contábeis do Brasil.
          </p>
        </div>

        <div class="card-subtle">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <div style="width:30px; height:30px; border-radius:8px; background:var(--accent-gold-soft); color:var(--accent-gold); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:13px;">
              🛡
            </div>
            <strong style="font-size:13px; color:var(--text-primary);">Seguro & Proteção</strong>
          </div>
          <p style="font-size:11.5px; color:var(--text-secondary); line-height:1.4;">
            Proteção de compras e seguro corporativo internacional para compras online e presenciais.
          </p>
        </div>

        <div class="card-subtle">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <div style="width:30px; height:30px; border-radius:8px; background:var(--accent-gold-soft); color:var(--accent-gold); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:13px;">
              ⚡
            </div>
            <strong style="font-size:13px; color:var(--text-primary);">Controle de Limites</strong>
          </div>
          <p style="font-size:11.5px; color:var(--text-secondary); line-height:1.4;">
            Defina tetos orçamentários por cartão e altere limites em tempo real pelo aplicativo desktop.
          </p>
        </div>
      </div>
    </div>
  `;
}
