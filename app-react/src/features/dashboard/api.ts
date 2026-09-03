import { env } from "@/config/env";
import { http } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type { AlertaUrgente, IndicadorDashboard, PontoTendencia } from "@/domain/types";

export interface ResumoDashboard {
  indicadores: IndicadorDashboard[];
  tendencia: PontoTendencia[];
  alertasUrgentes: AlertaUrgente[];
}

export async function buscarResumo(signal?: AbortSignal): Promise<ResumoDashboard> {
  if (env.useMocks) {
    return responderMock(
      {
        indicadores: fixtures.indicadoresDashboard,
        tendencia: fixtures.tendenciaProdutos,
        alertasUrgentes: fixtures.alertasUrgentes,
      },
      signal,
    );
  }

  const [status, alertas] = await Promise.all([
    http.get<{ mape_medio: number; produtos_monitorados: number; proximo_retrain: string }>(
      "/api/v1/models/status",
      signal ? { signal } : {},
    ),
    http.get<AlertaUrgente[]>("/api/v1/alerts", signal ? { signal } : {}),
  ]);

  const criticos = alertas.filter((alerta) => alerta.urgencia === "critico").length;

  return {
    indicadores: [
      { chave: "estoque-critico", valor: String(criticos), descricao: "Produtos com Estoque Crítico", tendencia: "alta" },
      {
        chave: "mape",
        valor: `${status.mape_medio.toFixed(1).replace(".", ",")}%`,
        descricao: "Precisão das Previsões (MAPE)",
        tendencia: "baixa",
        ajuda: "MAPE: quanto as previsões erram em média. Quanto menor, melhor.",
      },
      {
        chave: "produtos-monitorados",
        valor: String(status.produtos_monitorados),
        descricao: "Produtos Monitorados",
        tendencia: "neutra",
      },
      { chave: "proximo-calculo", valor: status.proximo_retrain, descricao: "Próximo Cálculo Automático", tendencia: "neutra" },
    ],
    tendencia: await http.get<PontoTendencia[]>("/api/v1/forecast/batch", signal ? { signal } : {}),
    alertasUrgentes: alertas,
  };
}
