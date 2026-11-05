/**
 * Fluxo 7 — Treinar previsões (gestora): confirmação, disparo e andamento no sino.
 * Roda depois da importação (06), que deixou vendas novas na base da execução. O treino
 * continua em segundo plano; o teste não espera ele terminar.
 */
import { expect, test } from "@playwright/test";
import { entrar, foto } from "./apoio";

test.describe("treinar previsões", () => {
  test("sino de notificações", async ({ page }) => {
    await entrar(page, "admin");
    await page.getByRole("button", { name: /notificaç/ }).click();
    await expect(page.getByRole("dialog").getByText("Notificações", { exact: true })).toBeVisible();
    await foto(page, "07-treino-notificacoes-antes", { inteira: false });
    await page.keyboard.press("Escape");
  });

  test("confirma e inicia o treino com as vendas novas", async ({ page }) => {
    await entrar(page, "admin");
    await page.getByRole("button", { name: "Treinar previsões" }).click();
    const modal = page.getByRole("alertdialog");
    await expect(modal.getByRole("heading", { name: "Treinar as previsões?" })).toBeVisible();
    await expect(modal.getByText(/Há dados novos desde o último treino/)).toBeVisible();
    await foto(page, "07-treino-confirmacao", { inteira: false });

    await modal.getByRole("button", { name: "Treinar agora" }).click();
    await expect(page.getByText("Treino iniciado. Acompanhe o andamento no sino de notificações.")).toBeVisible();
    await expect(page.getByRole("button", { name: /^Treinando\.\.\. \d+%$/ })).toBeVisible();
    await foto(page, "07-treino-iniciado", { inteira: false });

    await page.getByRole("button", { name: /notificaç/ }).click();
    await expect(page.getByRole("progressbar", { name: /Andamento do treino/ })).toBeVisible();
    await foto(page, "07-treino-andamento-no-sino", { inteira: false });
  });
});
