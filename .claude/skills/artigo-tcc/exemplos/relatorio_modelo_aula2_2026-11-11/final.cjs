const path = require("path");
const fs = require("fs");
const APP = "c:/Users/felip/OneDrive/Documentos/Estudos/TCC/TCC---Inventory-Forecasting/app-react";
const { chromium } = require(path.join(APP, "node_modules", "@playwright/test"));
const OUT = process.argv[2], XLSX = process.argv[3];
const FRONT = "http://localhost:5199";
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "pt-BR", timezoneId: "America/Sao_Paulo", acceptDownloads: true });
  const page = await ctx.newPage();
  const shot = async (name, full = true) => {
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.addStyleTag({ content: "*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important}" });
    await page.waitForTimeout(1800);
    if (!full) { await page.screenshot({ path: path.join(OUT, name + ".png") }); return; }
    const s = await page.addStyleTag({ content: ".h-screen{height:auto!important;min-height:100vh}.h-screen .overflow-hidden,main{overflow:visible!important}" });
    await page.screenshot({ path: path.join(OUT, name + ".png"), fullPage: true });
    await s.evaluate((el) => el.remove());
  };
  const wait = async () => { await page.waitForTimeout(500); await page.getByText(/^(Carregando|Abrindo|Retomando)/).first().waitFor({ state: "detached", timeout: 60000 }).catch(() => {}); };
  const go = async (item) => { await page.getByRole("navigation").getByRole("link", { name: item }).click(); await wait(); await page.mouse.move(5, 890); };
  await page.goto(FRONT + "/"); await page.waitForURL(/\/login$/);
  await page.waitForTimeout(1000);
  await shot("f_login", false);
  await page.getByLabel("E-mail").fill(process.env.EM);
  await page.getByLabel("Senha").fill(process.env.PW);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByRole("navigation").getByRole("link", { name: "Início" }).waitFor();
  await wait(); await page.mouse.move(5, 890);
  await shot("f_inicio");
  // notificações + botão treinar (viewport)
  const sino = page.locator('button[aria-label*="otificaç"]').first();
  await sino.click(); await page.waitForTimeout(1200);
  await shot("f_notificacoes", false);
  await page.keyboard.press("Escape");
  await go("Carregar Planilha"); await shot("f_importar", false);
  await page.locator('input[type="file"]').setInputFiles(XLSX);
  await page.getByText("Confira antes de gravar").waitFor({ timeout: 180000 });
  await page.mouse.move(5, 890);
  await shot("f_conferencia");
  // volta sem gravar
  await go("Conferir Dados"); await shot("f_conferir", false);
  await page.getByRole("button", { name: "Filtros" }).click().catch(() => {});
  await page.waitForTimeout(800); await shot("f_conferir_filtros", false); await page.keyboard.press("Escape");
  await go("Previsão de Vendas");
  await shot("f_previsao");
  // por produto
  const prod = page.getByRole("button", { name: /^Produto/ }).first();
  if (await prod.count()) { await prod.click(); await page.waitForTimeout(1500); await page.mouse.move(5, 890); await shot("f_previsao_produto"); }
  await page.getByRole("tab", { name: "Histórico de previsão" }).click(); await wait(); await page.mouse.move(5, 890);
  await shot("f_historico");
  await go("Relatórios"); await shot("f_relatorios", false);
  try {
    const dl = page.waitForEvent("download", { timeout: 60000 });
    await page.getByRole("button", { name: "PDF" }).first().click();
    const d = await dl; await d.saveAs(path.join(OUT, "relatorio_gerencial.pdf")); console.log("pdf ok", d.suggestedFilename());
  } catch (e) { console.log("sem download pdf", e.message); }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
