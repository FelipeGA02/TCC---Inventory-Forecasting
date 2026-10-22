interface Env {
  apiBaseUrl: string;
}

export const env: Env = {
  // VITE_API_URL; VITE_API_BASE_URL é o nome antigo, aceito para não quebrar .env já criados
  apiBaseUrl: (import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, ""),
};
