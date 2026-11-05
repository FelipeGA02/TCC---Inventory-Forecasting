/**
 * Fluxo 6 — Carregar Planilha: conferência antes de gravar, gravação e avisos.
 * Muda a base da execução (grava 02 a 07/03/2026): roda depois das telas de consulta.
 */
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { PLANILHA_COM_FALTA, PLANILHA_MARCO, PLANILHA_TEXTO } from "./ambiente";
import { entrar, esperarTela, foto, irPara } from "./apoio";

test.describe.configure({ mode: "serial" });

async function escolher(page: Page, arquivo: string): Promise<void> {
  await page.locator('input[type="file"]').setInputFiles(arquivo);
}

test.describe("carregar planilha", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "admin");
    await irPara(page, "Carregar Planilha", "Carregar Planilha de Vendas");
  });

  test("tela inicial com a lista de planilhas já carregadas", async ({ page }) => {
    await expect(page.getByText("Arraste e solte sua planilha aqui")).toBeVisible();
    // a planilha da base sintética: um cartão com o período (02/01 a 28/02)
    await expect(page.getByText("Planilhas já carregadas")).toBeVisible();
    await expect(page.getByText(/^1 planilhas · .* linhas · nenhuma duplicada$/)).toBeVisible();
    await foto(page, "06-importar-inicio");
  });

  test("recusa arquivo que não é planilha", async ({ page }) => {
    await escolher(page, PLANILHA_TEXTO);
    const erro = page.getByRole("alert");
    await expect(erro).toContainText("vendas.csv");
    await expect(erro).toContainText(".xlsx");
    await foto(page, "06-importar-arquivo-invalido");
  });

  test("confere, grava e oferece treinar", async ({ page }) => {
    await escolher(page, PLANILHA_MARCO);
    await expect(page.getByText("Confira antes de gravar")).toBeVisible();
    await expect(page.getByText(path.basename(PLANILHA_MARCO))).toBeVisible();
    await expect(page.getByText("última venda já carregada: 28/02/2026").first()).toBeVisible();
    await expect(page.getByText("Faltam vendas de alguns dias")).toHaveCount(0);
    await foto(page, "06-importar-conferencia");

    await page.getByRole("button", { name: "Gravar as vendas" }).click();
    await expect(page.getByText("Vendas novas gravadas")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("A previsão passa a usar estas vendas depois de treinar de novo.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Treinar previsões agora" })).toBeVisible();
    await foto(page, "06-importar-gravada");

    // a base das telas já vai até 07/03/2026
    await page.getByRole("button", { name: /Conferir os dados/ }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Conferir Dados" })).toBeVisible();
    await esperarTela(page);
    await expect(page.getByText("Dados até 07/03/2026")).toBeVisible();
  });

  test("a mesma planilha não é gravada duas vezes", async ({ page }) => {
    await escolher(page, PLANILHA_MARCO);
    await expect(page.getByRole("alert")).toContainText("já foi carregada");
    await foto(page, "06-importar-planilha-repetida");
  });

  test("avisa os dias de loja aberta que ficariam sem venda", async ({ page }) => {
    await escolher(page, PLANILHA_COM_FALTA);
    const aviso = page.getByRole("alert");
    await expect(aviso).toContainText("Faltam vendas de alguns dias");
    await expect(aviso).toContainText("09/03/2026 a 10/03/2026");
    await expect(page.getByRole("button", { name: "Gravar mesmo assim" })).toBeVisible();
    await foto(page, "06-importar-dias-faltando");
    // cancelar não grava nada
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByText("Arraste e solte sua planilha aqui")).toBeVisible();
  });
});
