/** Fluxo 2 — Início: visão geral das vendas, filtro de loja e medidas. */
import { expect, test } from "@playwright/test";
import { entrar, foto } from "./apoio";

test.describe("início", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "admin");
  });

  test("mostra os indicadores e os gráficos da base inteira", async ({ page }) => {
    await expect(page.getByRole("heading", { level: 1, name: "Início" })).toBeVisible();
    for (const kpi of ["Faturamento líquido", "Notas de venda", "Quantidade vendida", "Encomendas grandes"]) {
      await expect(page.getByText(kpi, { exact: true }).first()).toBeVisible();
    }
    for (const card of ["Faturamento por mês", "Faturamento médio por dia da semana", "Mix por categoria",
      "Formas de pagamento"]) {
      await expect(page.getByText(card, { exact: true })).toBeVisible();
    }
    // a base sintética vai de 02/01/2025 a 28/02/2026
    await expect(page.getByText("Base de vendas de")).toContainText("28/02/2026");
    await expect(page.getByText("Dados até 28/02/2026")).toBeVisible();
    await foto(page, "02-inicio-todas-as-lojas");
  });

  test("filtra por loja", async ({ page }) => {
    const loja = page.getByRole("radiogroup", { name: "Loja" });
    for (const nome of ["Jardim Canadá", "Itabirito"]) {
      await loja.getByRole("radio", { name: nome }).click();
      await expect(loja.getByRole("radio", { name: nome })).toHaveAttribute("aria-checked", "true");
      await foto(page, `02-inicio-${nome === "Itabirito" ? "itabirito" : "jardim-canada"}`);
    }
  });

  test("troca faturamento por quantidade", async ({ page }) => {
    await page.getByRole("radiogroup", { name: "Mostrar" }).first().getByRole("radio", { name: "Quantidade" }).click();
    await expect(page.getByText("Quantidade vendida por mês")).toBeVisible();
    await foto(page, "02-inicio-quantidade");
  });

  test("botão Atualizar recarrega os dados", async ({ page }) => {
    await page.getByRole("button", { name: "Atualizar" }).click();
    await expect(page.getByText("Dados atualizados.")).toBeVisible();
  });
});
