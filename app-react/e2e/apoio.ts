/** Ações comuns dos testes: entrar, esperar a tela carregar e tirar a foto do fluxo. */
import { expect, type Page } from "@playwright/test";
import path from "node:path";
import { PASTA_FOTOS, USUARIOS, type Perfil } from "./ambiente";

/** Faz login pela tela de login e espera o layout autenticado. */
export async function entrar(page: Page, perfil: Perfil = "admin", destino = "/"): Promise<void> {
  const u = USUARIOS[perfil];
  await page.goto(destino);
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("E-mail").fill(u.email);
  await page.getByLabel("Senha").fill(u.senha);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("navigation").getByRole("link", { name: "Início" })).toBeVisible();
  await esperarTela(page);
}

/** Espera sumirem as telas de "Carregando..." (contexto, dados da rota, sessão). */
export async function esperarTela(page: Page): Promise<void> {
  await expect(page.getByText(/^(Carregando|Abrindo|Retomando)/)).toHaveCount(0, { timeout: 30_000 });
}

/** Vai para uma tela pelo menu lateral e espera os dados dela. */
export async function irPara(page: Page, item: string, titulo: string): Promise<void> {
  await page.getByRole("navigation").getByRole("link", { name: item }).click();
  await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
  await esperarTela(page);
}

/**
 * Foto da tela inteira em `e2e/fotos/<nome>.png`. O layout rola dentro do `<main>` (altura
 * da janela), então a foto solta a altura por um instante para sair a página toda.
 * Com `inteira: false`, só a janela visível (para modal, menu ou popover aberto, que sairia
 * deslocado com a página solta).
 */
export async function foto(page: Page, nome: string, opcoes: { inteira?: boolean } = {}): Promise<void> {
  const arquivo = path.join(PASTA_FOTOS, `${nome}.png`);
  await page.waitForLoadState("networkidle").catch(() => undefined);
  // animações (gráficos, spinners, toasts) param para a foto sair igual em toda execução
  await page.addStyleTag({ content: "*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important}" });
  if (opcoes.inteira === false) {
    await page.screenshot({ path: arquivo });
    return;
  }
  const solto = await page.addStyleTag({
    content: ".h-screen{height:auto!important;min-height:100vh}.h-screen .overflow-hidden,main{overflow:visible!important}",
  });
  await page.screenshot({ path: arquivo, fullPage: true });
  await solto.evaluate((el) => el.remove());
}
