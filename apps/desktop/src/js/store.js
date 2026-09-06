// Secure store abstraction for Tauri Desktop
import { CONFIG } from './config.js';

let tauriStore = null;
let isTauri = false;

// In-memory cache for ultra-fast access
const cache = {
  theme: localStorage.getItem('bankcore_desktop_theme') || 'light',
  hide_balance: localStorage.getItem('bankcore_desktop_hide_balance') === 'true',
  api_endpoint: localStorage.getItem('bankcore_desktop_api') || CONFIG.apiBaseUrl,
  auth_token: null,
  auth_user: null,
  auth_account: null,
};

export async function initStore() {
  try {
    if (window.__TAURI_INTERNALS__ || window.__TAURI__) {
      const { Store } = await import('@tauri-apps/plugin-store');
      tauriStore = await Store.load('bankcore_secure_vault.bin');
      isTauri = true;

      // Load persisted settings
      const savedTheme = await tauriStore.get('theme');
      if (savedTheme) cache.theme = savedTheme;

      const savedHideBalance = await tauriStore.get('hide_balance');
      if (savedHideBalance !== null && savedHideBalance !== undefined) {
        cache.hide_balance = Boolean(savedHideBalance);
      }

      const savedEndpoint = await tauriStore.get('api_endpoint');
      if (savedEndpoint) cache.api_endpoint = savedEndpoint;

      const savedToken = await tauriStore.get('auth_token');
      if (savedToken) cache.auth_token = savedToken;

      const savedUser = await tauriStore.get('auth_user');
      if (savedUser) cache.auth_user = savedUser;

      const savedAccount = await tauriStore.get('auth_account');
      if (savedAccount) cache.auth_account = savedAccount;
    }
  } catch (err) {
    console.warn('Tauri Store not available, using in-memory/session fallback:', err);
  }
  return cache;
}

export async function getSecureItem(key) {
  return cache[key];
}

export async function setSecureItem(key, value) {
  cache[key] = value;
  if (isTauri && tauriStore) {
    try {
      await tauriStore.set(key, value);
      await tauriStore.save();
    } catch (e) {
      console.warn('Error writing to Tauri Store:', e);
    }
  } else {
    // Web fallback for non-sensitive preferences
    if (key === 'theme' || key === 'hide_balance' || key === 'api_endpoint') {
      localStorage.setItem(`bankcore_desktop_${key}`, String(value));
    }
  }
}

export async function removeSecureItem(key) {
  delete cache[key];
  if (isTauri && tauriStore) {
    try {
      await tauriStore.delete(key);
      await tauriStore.save();
    } catch (e) {
      console.warn('Error deleting from Tauri Store:', e);
    }
  } else {
    localStorage.removeItem(`bankcore_desktop_${key}`);
  }
}

export async function clearAuthSession() {
  cache.auth_token = null;
  cache.auth_user = null;
  cache.auth_account = null;
  if (isTauri && tauriStore) {
    try {
      await tauriStore.delete('auth_token');
      await tauriStore.delete('auth_user');
      await tauriStore.delete('auth_account');
      await tauriStore.save();
    } catch (e) {
      console.warn('Error clearing auth from Tauri Store:', e);
    }
  }
}
