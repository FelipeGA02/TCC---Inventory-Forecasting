/** Fluxo 3 — Conferir Dados: registros importados, abas, busca, filtros, nota e exportação. */
import { expect, test } from "@playwright/test";
import { entrar, esperarTela, foto, irPara } from "./apoio";

test.describe("conferir dados", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "viewer");
    await irPara(page, "Conferir Dados", "Conferir Dados");
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("lista os registros com as abas de visão rápida", async ({ page }) => {
    const abas = page.getByRole("tablist");
    for (const aba of ["Todos", "Encomendas grandes", "Clientes cadastrados", "Com desconto", "Devoluções"]) {
      await expect(abas.getByRole("tab", { name: new RegExp(aba) })).toBeVisible();
    }
    await expect(page.getByRole("navigation", { name: "Paginação" })).toBeVisible();
    await foto(page, "03-conferir-dados-todos");
  });

  test("aba de encomendas grandes explica o limite", async ({ page }) => {
    await page.getByRole("tab", { name: /Encomendas grandes/ }).click();
    await expect(page.getByText(/Encomenda grande é a nota bem acima do tamanho habitual/)).toBeVisible();
    await esperarTela(page);
    await foto(page, "03-conferir-dados-encomendas-grandes");
  });

  test("busca por produto", async ({ page }) => {
    await page.getByPlaceholder("Buscar por produto, código ou nº da nota").fill("ESMERALDA");
    await expect(page.getByRole("table").getByText("GRAMA ESMERALDA M2").first()).toBeVisible();
    await expect(page.getByRole("table").getByText("TERRA VEGETAL 25KG")).toHaveCount(0);
    await foto(page, "03-conferir-dados-busca");
    await page.getByRole("button", { name: "Limpar busca" }).click();
    await expect(page.getByRole("table").getByText("TERRA VEGETAL 25KG").first()).toBeVisible();
  });

  test("painel de filtros", async ({ page }) => {
    await page.getByRole("button", { name: /^Filtros/ }).click();
    const painel = page.getByRole("dialog");
    await expect(painel.getByText("Loja", { exact: true })).toBeVisible();
    await expect(painel.getByText("Categoria", { exact: true })).toBeVisible();
    await foto(page, "03-conferir-dados-filtros", { inteira: false });
    await page.keyboard.press("Escape");
  });

  test("abre a nota ao clicar na linha", async ({ page }) => {
    await page.getByRole("table").getByRole("row").nth(1).click();
    const nota = page.getByRole("dialog");
    await expect(nota.getByRole("heading", { name: /^Nota / })).toBeVisible();
    await expect(nota.getByText("…")).toHaveCount(0);
    await foto(page, "03-conferir-dados-nota", { inteira: false });
  });

  test("escolhe as colunas visíveis", async ({ page }) => {
    await page.getByRole("button", { name: "Colunas" }).click();
    await expect(page.getByRole("menu")).toContainText("Colunas visíveis");
    await foto(page, "03-conferir-dados-colunas", { inteira: false });
    await page.keyboard.press("Escape");
  });

  test("exporta os registros filtrados em Excel e CSV", async ({ page }) => {
    for (const [opcao, extensao] of [["Excel (.xlsx)", ".xlsx"], ["CSV", ".csv"]] as const) {
      await page.getByRole("button", { name: "Exportar" }).click();
      if (extensao === ".xlsx") await foto(page, "03-conferir-dados-exportar", { inteira: false });
      const download = page.waitForEvent("download");
      await page.getByRole("menuitem", { name: opcao }).click();
      expect((await download).suggestedFilename()).toMatch(new RegExp(`\\${extensao}$`));
    }
  });
});
