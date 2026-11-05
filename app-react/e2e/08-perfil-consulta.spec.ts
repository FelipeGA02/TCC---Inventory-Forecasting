/** Fluxo 8 — Perfil de consulta (gerente): vê tudo, mas não carrega planilha nem treina. */
import { expect, test } from "@playwright/test";
import { entrar, foto, irPara } from "./apoio";

test.describe("perfil de consulta", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "viewer");
  });

  test("não vê o botão de treinar", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Atualizar" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Treinar previsões|Treinando/ })).toHaveCount(0);
  });

  test("carregar planilha fica bloqueado", async ({ page }) => {
    await irPara(page, "Carregar Planilha", "Carregar Planilha de Vendas");
    await expect(page.getByText("Só a gestora carrega planilhas")).toBeVisible();
    await expect(page.locator('input[type="file"]')).toHaveCount(0);
    await foto(page, "08-consulta-importar-bloqueado");
  });
});
