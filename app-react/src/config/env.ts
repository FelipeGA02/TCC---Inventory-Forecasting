interface Env {
  apiBaseUrl: string;
  useMocks: boolean;
  mockLatencyMs: number;
}

function bool(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  return value === "true" || value === "1";
}

export const env: Env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  useMocks: bool(import.meta.env.VITE_USE_MOCKS, import.meta.env.DEV),
  mockLatencyMs: Number(import.meta.env.VITE_MOCK_LATENCY_MS ?? 300),
};
