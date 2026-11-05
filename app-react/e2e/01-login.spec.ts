/** Fluxo 1 — Login, sessão e saída. */
import { expect, test } from "@playwright/test";
import { USUARIOS } from "./ambiente";
import { entrar, esperarTela, foto } from "./apoio";

test.describe("login", () => {
  test("sem sessão, qualquer página manda para o login", async ({ page }) => {
    await page.goto("/previsao");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("button", { name: "Entrar" })).toBeDisabled();
    await foto(page, "01-login-tela");
  });

  test("senha errada mostra o aviso e não entra", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail").fill(USUARIOS.admin.email);
    await page.getByLabel("Senha").fill("senha-errada");
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page.getByRole("alert")).toHaveText("E-mail ou senha incorretos.");
    await expect(page).toHaveURL(/\/login$/);
    await foto(page, "01-login-senha-errada");
  });

  test("depois do login volta para a página pedida", async ({ page }) => {
    await entrar(page, "admin", "/previsao");
    await expect(page).toHaveURL(/\/previsao$/);
    await expect(page.getByRole("heading", { level: 1, name: "Previsão de Vendas" })).toBeVisible();
  });

  test("a sessão continua depois de recarregar a página", async ({ page }) => {
    await entrar(page, "viewer");
    await page.reload();
    await esperarTela(page);
    await expect(page.getByRole("heading", { level: 1, name: "Início" })).toBeVisible();
  });

  test("menu da conta mostra o perfil e sai do sistema", async ({ page }) => {
    await entrar(page, "admin");
    await page.getByRole("button", { name: "Conta e sair" }).click();
    const menu = page.getByRole("menu");
    await expect(menu).toContainText(USUARIOS.admin.email);
    await expect(menu).toContainText(USUARIOS.admin.nome);
    await foto(page, "01-login-menu-da-conta", { inteira: false });
    await menu.getByRole("menuitem", { name: /Sair/ }).click();
    await expect(page).toHaveURL(/\/login$/);
    // sem sessão de novo: a página protegida volta para o login
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
  });
});
