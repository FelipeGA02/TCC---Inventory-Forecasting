import { env } from "@/config/env";
import { http } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type {
  EventoSazonal,
  LinhaPrevisaoSemanal,
  MetricaModelo,
  PontoPrevisao,
  Produto,
  Unidade,
} from "@/domain/types";

export interface ParametrosPrevisao {
  produtoId: string;
  unidadeId: string;
  horizonte: number;
}

export interface Previsao {
  serie: PontoPrevisao[];
  recomendacaoSemanal: LinhaPrevisaoSemanal[];
  metricas: MetricaModelo[];
  eventos: EventoSazonal[];
}

export async function buscarCatalogo(
  signal?: AbortSignal,
): Promise<{ produtos: Produto[]; unidades: Unidade[] }> {
  if (env.useMocks) {
    return responderMock({ produtos: fixtures.produtos, unidades: fixtures.unidades }, signal);
  }

  return {
    produtos: await http.get<Produto[]>("/api/v1/products", signal ? { signal } : {}),

    unidades: fixtures.unidades,
  };
}

export async function buscarPrevisao(
  parametros: ParametrosPrevisao,
  signal?: AbortSignal,
): Promise<Previsao> {
  if (env.useMocks) {
    return responderMock(
      {
        serie: fixtures.previsaoSarimax,
        recomendacaoSemanal: fixtures.tabelaPrevisaoSemanal.slice(0, parametros.horizonte),
        metricas: fixtures.metricasModelo,
        eventos: fixtures.eventosSazonais,
      },
      signal,
    );
  }

  return http.get<Previsao>(`/api/v1/forecast/${encodeURIComponent(parametros.produtoId)}`, {
    query: { unidade: parametros.unidadeId, horizonte: parametros.horizonte },
    ...(signal ? { signal } : {}),
  });
}
