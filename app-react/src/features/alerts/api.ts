import { env } from "@/config/env";
import { http } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type { AlertaReposicao } from "@/domain/types";

export interface FiltroAlertas {
  unidade: string;
  grupo: string;
}

export async function buscarAlertas(
  filtro: FiltroAlertas,
  signal?: AbortSignal,
): Promise<AlertaReposicao[]> {
  if (env.useMocks) return responderMock(fixtures.alertasReposicao, signal);

  return http.get<AlertaReposicao[]>("/api/v1/alerts", {
    query: {
      unidade: filtro.unidade === "todos" ? undefined : filtro.unidade,
      grupo: filtro.grupo === "todos" ? undefined : filtro.grupo,
    },
    ...(signal ? { signal } : {}),
  });
}
