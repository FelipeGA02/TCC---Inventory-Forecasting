/** Fluxo 4 — Previsão de Vendas: 14 dias por categoria e por produto de grama, e o histórico. */
import { expect, test, type Page } from "@playwright/test";
import { entrar, esperarTela, foto, irPara } from "./apoio";

const cartaoPrevisao = (page: Page) =>
  page.locator("div.border").filter({ has: page.getByText("Previsão dos próximos 14 dias", { exact: true }) }).first();

test.describe("previsão de vendas", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "viewer");
    await irPara(page, "Previsão de Vendas", "Previsão de Vendas");
  });

  test("previsão por categoria de cada loja", async ({ page }) => {
    await expect(page.getByRole("tab", { name: /Previsão/ })).toHaveAttribute("aria-selected", "true");
    const cartao = cartaoPrevisao(page);
    await expect(cartao).toBeVisible();
    await expect(page.getByText("Dia a dia", { exact: true })).toBeVisible();
    await foto(page, "04-previsao-categorias-jardim-canada");

    await cartao.getByRole("radiogroup", { name: "Unidade" }).getByRole("radio", { name: "Itabirito" }).click();
    await foto(page, "04-previsao-categorias-itabirito");
  });

  test("previsão por produto de grama e detalhe do produto", async ({ page }) => {
    const cartao = cartaoPrevisao(page);
    await cartao.getByRole("radiogroup", { name: "Por" }).getByRole("radio", { name: /^Produto \(\d+\)$/ }).click();
    await cartao.getByRole("button", { name: /GRAMA ESMERALDA M2/ }).click();
    await expect(page.getByText("Ver histórico deste produto")).toBeVisible();
    await expect(page.getByText(/cód\. 100 · Grama/)).toBeVisible();
    await foto(page, "04-previsao-produto-grama");

    // "Ver histórico deste produto" abre a aba de histórico com o produto escolhido
    await page.getByText("Ver histórico deste produto").click();
    await expect(page.getByRole("tab", { name: "Histórico de previsão" })).toHaveAttribute("aria-selected", "true");
    await esperarTela(page);
    await foto(page, "04-previsao-historico-do-produto");
  });

  test("tabela dia a dia por produto, com busca", async ({ page }) => {
    const filtros = page.getByRole("radiogroup", { name: "Mostrar" });
    await filtros.getByRole("radio", { name: "Produtos" }).click();
    await page.getByPlaceholder("Buscar produto ou código").last().fill("SAO CARLOS");
    await expect(page.getByRole("table").getByText(/GRAMA SAO CARLOS M2/).first()).toBeVisible();
    await foto(page, "04-previsao-dia-a-dia-produtos");
  });

  test("histórico de previsão: vendido × previsto por categoria", async ({ page }) => {
    await page.getByRole("tab", { name: "Histórico de previsão" }).click();
    await esperarTela(page);
    await expect(page.getByText("Histórico de previsão", { exact: true }).last()).toBeVisible();
    const periodo = page.getByRole("radiogroup", { name: "Período" });
    for (const [rotulo, arquivo] of [["Últimos 3 meses", "3-meses"], ["Último ano", "ultimo-ano"]] as const) {
      await periodo.getByRole("radio", { name: rotulo }).click();
      await esperarTela(page);
      await foto(page, `04-previsao-historico-categoria-${arquivo}`);
    }
  });
});
