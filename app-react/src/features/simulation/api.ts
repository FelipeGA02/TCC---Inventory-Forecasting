import { env } from "@/config/env";
import { http } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type { PontoSimulacao, Produto } from "@/domain/types";

export async function buscarLinhaDeBase(
  produtoId: string,
  signal?: AbortSignal,
): Promise<{ base: PontoSimulacao[]; produtos: Produto[] }> {
  if (env.useMocks) {
    return responderMock({ base: fixtures.dadosSimulacaoBase, produtos: fixtures.produtos }, signal);
  }

  return {
    base: await http.get<PontoSimulacao[]>("/api/v1/simulation", {
      query: { produto_cod: produtoId },
      ...(signal ? { signal } : {}),
    }),
    produtos: await http.get<Produto[]>("/api/v1/products", signal ? { signal } : {}),
  };
}
