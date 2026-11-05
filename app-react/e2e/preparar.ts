/** Antes dos testes: gera as planilhas "Contas a Receber" do fluxo de importação. */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { IA_PREDICTOR, PASTA_FOTOS, PASTA_SAIDA, PLANILHA_COM_FALTA, PLANILHA_MARCO, PLANILHA_TEXTO, PYTHON } from "./ambiente";

function planilha(caminho: string, inicio: string, fim: string): void {
  execFileSync(PYTHON, ["-m", "tests.e2e.servidor", "--planilha", caminho, "--inicio", inicio, "--fim", fim], {
    cwd: IA_PREDICTOR,
    stdio: "inherit",
  });
}

export default function preparar(): void {
  mkdirSync(PASTA_SAIDA, { recursive: true });
  mkdirSync(PASTA_FOTOS, { recursive: true });
  // continua a base (que vai até 28/02/2026): sem dias faltando
  planilha(PLANILHA_MARCO, "2026-03-02", "2026-03-07");
  // depois da de cima, pula 09 e 10/03 (segunda e terça): a conferência avisa
  planilha(PLANILHA_COM_FALTA, "2026-03-11", "2026-03-13");
  writeFileSync(PLANILHA_TEXTO, "data;produto;quantidade\n02/03/2026;GRAMA;10\n");
}
