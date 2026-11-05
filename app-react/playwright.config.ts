/**
 * Testes de ponta a ponta (Playwright): o front de verdade conversando com a API de verdade.
 *
 * O Playwright sobe os dois servidores sozinho, em portas próprias, para não brigar com o
 * `npm run dev` (5173) nem com a API de desenvolvimento (8000):
 *   - API em 8100: `ia-predictor/tests/e2e/servidor.py` — SQLite temporário com base
 *     sintética e um treino concluído. Nunca toca o Neon nem o banco do `.env`.
 *   - Front em 5174: Vite apontando para a API dos testes.
 *
 * As fotos de cada fluxo ficam em `e2e/fotos/` (ver `e2e/apoio.ts`). Como rodar: `e2e/README.md`.
 */
import { defineConfig, devices } from "@playwright/test";
import { API_PORTA, API_URL, FRONT_PORTA, FRONT_URL, IA_PREDICTOR, PYTHON } from "./e2e/ambiente";

export default defineConfig({
  testDir: "./e2e",
  // Os testes compartilham o banco da execução (a planilha enviada muda a base): um de
  // cada vez, na ordem dos arquivos (01-, 02-, ...).
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  globalSetup: "./e2e/preparar.ts",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: FRONT_URL,
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    acceptDownloads: true,
  },
  projects: [{ name: "chromium" }],
  webServer: [
    {
      command: `"${PYTHON}" -m tests.e2e.servidor --porta ${API_PORTA} --origem ${FRONT_URL}`,
      cwd: IA_PREDICTOR,
      url: `${API_URL}/health`,
      // A 1ª execução monta a base sintética e treina (~2–5 min); depois sai do cache.
      timeout: 600_000,
      reuseExistingServer: false,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npx vite --port ${FRONT_PORTA} --strictPort`,
      url: FRONT_URL,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VITE_API_URL: API_URL },
    },
  ],
});
