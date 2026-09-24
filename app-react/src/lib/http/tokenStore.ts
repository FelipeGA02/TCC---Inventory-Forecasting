const REFRESH_KEY = "floricultura.refresh_token";

let accessToken: string | null = null;
let expiraEm = 0;

type Listener = () => void;
const listeners = new Set<Listener>();

function notificar(): void {
  for (const listener of listeners) listener();
}

export const tokenStore = {
  getAccessToken: (): string | null => accessToken,

  getRefreshToken: (): string | null => {
    try {
      return localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  },

  isAccessTokenValido: (): boolean => accessToken !== null && Date.now() < expiraEm - 30_000,

  setAccessToken: (token: string, expiresInSeconds: number): void => {
    accessToken = token;
    expiraEm = Date.now() + expiresInSeconds * 1000;
    notificar();
  },

  setRefreshToken: (token: string): void => {
    try {
      localStorage.setItem(REFRESH_KEY, token);
    } catch {
    }
  },

  limpar: (): void => {
    accessToken = null;
    expiraEm = 0;
    try {
      localStorage.removeItem(REFRESH_KEY);
    } catch {
    }
    notificar();
  },

  subscribe: (listener: Listener): (() => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
