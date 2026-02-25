import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';

const matchMediaMock = (query) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
});

if (!window.matchMedia) {
  window.matchMedia = matchMediaMock;
}

if (!window.localStorage || typeof window.localStorage.clear !== 'function') {
  const storage = new Map();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => (storage.has(key) ? storage.get(key) : null),
      setItem: (key, value) => storage.set(key, String(value)),
      removeItem: (key) => storage.delete(key),
      clear: () => storage.clear(),
    },
  });
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

if (!window.ENV) {
  window.ENV = {};
}
window.ENV.HASURA_ADMIN_SECRET = 'test-secret';

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();

  globalThis.fetch = vi.fn(async (input) => {
    const url = typeof input === 'string' ? input : input.url;

    if (url.includes('/api/system/available-services')) {
      return {
        ok: true,
        json: async () => ({ services: [] }),
      };
    }

    if (url.includes('/hasura/v1/graphql')) {
      return {
        ok: true,
        json: async () => ({
          data: {
            findings_aggregate: {
              aggregate: { count: 0 },
            },
          },
        }),
      };
    }

    return {
      ok: true,
      json: async () => ({}),
      text: async () => '',
    };
  });
});

afterEach(() => {
  cleanup();
});
