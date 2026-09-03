import { env } from "@/config/env";
import { http, request } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type { RelatorioGerado } from "@/domain/types";

export interface ParametrosExportacao {
  periodo: string;
  unidade: string;
  grupo: string;
  formato: "pdf" | "xlsx";
}

export async function buscarHistorico(signal?: AbortSignal): Promise<RelatorioGerado[]> {
  if (env.useMocks) return responderMock(fixtures.historicoRelatorios, signal);
  return http.get<RelatorioGerado[]>("/api/v1/reports/export", signal ? { signal } : {});
}

export async function exportarRelatorio(parametros: ParametrosExportacao): Promise<void> {
  if (env.useMocks) {
    await responderMock(undefined);
    return;
  }

  const blob = await request<Blob>("/api/v1/reports/export", {
    method: "POST",
    body: {
      periodo: parametros.periodo,
      unidade: parametros.unidade === "todos" ? undefined : parametros.unidade,
      grupo: parametros.grupo === "todos" ? undefined : parametros.grupo,
      formato: parametros.formato,
    },
    blob: true,
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `relatorio-${parametros.periodo}.${parametros.formato}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
