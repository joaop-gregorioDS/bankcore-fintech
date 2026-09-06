// BankCore Desktop API Client
import { getSecureItem, clearAuthSession } from './store.js';
import { CONFIG } from './config.js';

export class ApiError extends Error {
  constructor(status, message, details = null) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

async function request(path, options = {}) {
  const baseUrl = CONFIG.apiBaseUrl;
  const url = `${baseUrl.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;

  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers || {}),
  };

  const token = await getSecureItem('auth_token');
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    await clearAuthSession();
    window.dispatchEvent(new CustomEvent('bankcore:unauthorized'));
    throw new ApiError(401, 'Sessão expirada. Faça login novamente.');
  }

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  } else {
    data = await response.text().catch(() => null);
  }

  if (!response.ok) {
    let msg = `Erro ${response.status}`;
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') msg = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) msg = data.detail[0].msg;
    }
    throw new ApiError(response.status, msg, data);
  }

  return data;
}

export const api = {
  // Auth
  async login(taxId, password) {
    const cleanTaxId = String(taxId).replace(/\D/g, '');
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ tax_id: cleanTaxId, password }),
    });
  },

  async getMe() {
    return request('/auth/me');
  },

  async lookupDirectory(taxId) {
    const cleanTaxId = String(taxId).replace(/\D/g, '');
    return request(`/auth/directory/${cleanTaxId}`);
  },

  // Accounts
  async getOrCreateAccount(userId) {
    return request('/accounts/', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
  },

  async getAccount(accountId) {
    return request(`/accounts/${accountId}`);
  },

  async getStatement(accountId) {
    return request(`/accounts/${accountId}/statement`);
  },

  // Transactions
  async deposit(accountId, amountReais, idempotencyKey = null) {
    const key = idempotencyKey || `dep_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
    return request('/transactions/deposit', {
      method: 'POST',
      body: JSON.stringify({
        account_id: accountId,
        amount_reais: Number(amountReais),
        idempotency_key: key,
      }),
    });
  },

  async transferPix(sourceAccountId, destinationCpf, amountReais, description = 'Pix BankCore Desktop') {
    const cleanKey = String(destinationCpf).replace(/\D/g, '');
    const key = `pix_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
    return request('/transactions/pix', {
      method: 'POST',
      body: JSON.stringify({
        source_account_id: sourceAccountId,
        destination_key: cleanKey,
        amount_reais: Number(amountReais),
        idempotency_key: key,
        description,
      }),
    });
  },
};
