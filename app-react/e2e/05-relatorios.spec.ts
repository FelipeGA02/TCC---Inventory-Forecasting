/** Fluxo 5 — Relatórios: catálogo, prévia, filtros e download em Excel e CSV. */
import { expect, test } from "@playwright/test";
import { entrar, foto, irPara } from "./apoio";

// Os relatórios do catálogo (src/app/data/relatorios.ts) e o nome da foto de cada um.
const RELATORIOS = [
  ["Previsão por produto de grama", "previsao-grama"],
  ["Vendas por semana · base completa", "vendas-por-semana"],
  ["Vendas por dia · últimas 8 semanas", "vendas-por-dia"],
  ["Encomendas grandes por semana", "encomendas-grandes"],
  ["Acerto da previsão de cada categoria", "acerto-categorias"],
  ["Acerto de cada produto de grama", "acerto-grama"],
  ["Teste de acerto por categoria · dia a dia", "teste-de-acerto"],
  ["Planilhas importadas", "planilhas-importadas"],
] as const;

test.describe("relatórios", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "viewer");
    await irPara(page, "Relatórios", "Relatórios");
  });

  test("relatório gerencial e catálogo", async ({ page }) => {
    await expect(page.getByText("Relatório gerencial")).toBeVisible();
    await expect(page.getByRole("button", { name: "Gerar PDF" })).toBeVisible();
    await expect(page.getByText("Relatórios disponíveis")).toBeVisible();
    await foto(page, "05-relatorios-inicio");
  });

  for (const [titulo, arquivo] of RELATORIOS) {
    test(`prévia: ${titulo}`, async ({ page }) => {
      await page.getByRole("button", { name: new RegExp(`^${titulo.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`) }).click();
      await expect(page.getByText(titulo, { exact: true }).last()).toBeVisible();
      await expect(page.getByText("Para que serve:")).toBeVisible();
      await foto(page, `05-relatorios-${arquivo}`);
    });
  }

  test("baixa o relatório em Excel e em CSV", async ({ page }) => {
    await page.getByRole("button", { name: /^Vendas por semana · base completa/ }).click();
    for (const [botao, extensao] of [["Baixar Excel", ".xlsx"], ["Baixar CSV", ".csv"]] as const) {
      const download = page.waitForEvent("download");
      await page.getByRole("button", { name: new RegExp(`^${botao}`) }).click();
      expect((await download).suggestedFilename()).toMatch(new RegExp(`\\${extensao}$`));
    }
    // o histórico de baixados guarda os dois
    await expect(page.getByText(/baixad/i).first()).toBeVisible();
    await foto(page, "05-relatorios-baixados");
  });
});
