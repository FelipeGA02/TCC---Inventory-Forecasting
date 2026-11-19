// Captura as telas das Figuras 9 a 13 do sistema em execução (front 5173 → API 8000, base de demonstração).
// Uso: node capturar.mjs <raiz-do-repo> <pasta-saida>
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const [raiz, saida] = process.argv.slice(2);
const require = createRequire(path.join(raiz, "app-react", "package.json"));
const { chromium } = require("@playwright/test");
const env = Object.fromEntries(
  fs.readFileSync(path.join(raiz, "ia-predictor", ".env"), "utf8").split(/\r?\n/)
    .filter((l) => /^[A-Z_]+=/.test(l)).map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1).trim()]),
);
const URL = "http://localhost:5173";
const PLANILHA = path.join(raiz, "ia-predictor", "tests", "upload_marco_2026", "marco_2026_com_erros.xlsx");
fs.mkdirSync(saida, { recursive: true });

const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const calmo = async () => {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.getByText(/^(Carregando|Abrindo|Retomando)/).first().waitFor({ state: "detached", timeout: 60000 }).catch(() => undefined);
  await page.addStyleTag({ content: "*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important}" });
  await page.waitForTimeout(2500);
};
const foto = async (nome, altura) => {
  await page.setViewportSize({ width: 1440, height: altura });
  await page.mouse.move(1435, altura - 5);
  await calmo();
  await page.screenshot({ path: path.join(saida, nome + ".png"), clip: { x: 0, y: 0, width: 1440, height: altura } });
  console.log("ok", nome);
};
const ir = async (item, titulo) => {
  await page.getByRole("navigation").getByRole("link", { name: item }).click();
  await page.getByRole("heading", { level: 1, name: titulo }).waitFor();
  await calmo();
};

await page.goto(URL + "/");
await page.getByLabel("E-mail").fill(env.ADMIN_EMAIL);
await page.getByLabel("Senha").fill(env.ADMIN_PASSWORD);
await page.getByRole("button", { name: "Entrar" }).click();
await page.getByRole("navigation").getByRole("link", { name: "Início" }).waitFor({ timeout: 60000 });
await page.getByRole("heading", { level: 1, name: "Início" }).waitFor();
await foto("fig09_inicio", 735);

// Figura 10: conferência da planilha de teste (só confere, não grava)
await ir("Carregar Planilha", "Carregar Planilha de Vendas");
await page.locator('input[type="file"]').setInputFiles(PLANILHA);
await page.getByText("Confira antes de gravar").waitFor({ timeout: 180000 });
await foto("fig10_conferencia", 740);
const cancelar = page.getByRole("button", { name: "Cancelar" });
if (await cancelar.count()) await cancelar.first().click();

// Figura 11: previsão por categoria, Jardim Canadá, 2 semanas
await ir("Previsão de Vendas", "Previsão de Vendas");
await foto("fig11_previsao", 905);

// Figura 12: histórico de previsão, Grama de Jardim Canadá, últimos 3 meses
await page.getByRole("tab", { name: "Histórico de previsão" }).click();
await page.getByText("Histórico de previsão", { exact: true }).last().waitFor();
await foto("fig12_historico", 920);

// Figura 13: relatórios, todas as lojas
await ir("Relatórios", "Relatórios");
await foto("fig13_relatorios", 900);

await browser.close();
