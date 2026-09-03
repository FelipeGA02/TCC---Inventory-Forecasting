import { env } from "@/config/env";
import { http } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import * as fixtures from "@/services/mocks/fixtures";
import type { RegistroImportado } from "@/domain/types";

export async function buscarRegistrosImportados(
  signal?: AbortSignal,
): Promise<RegistroImportado[]> {
  if (env.useMocks) return responderMock(fixtures.tabelaPreVisualizacao, signal);
  return http.get<RegistroImportado[]>("/api/v1/upload/preview", signal ? { signal } : {});
}
