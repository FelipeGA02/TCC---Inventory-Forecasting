import { env } from "@/config/env";
import { request } from "@/lib/http/client";
import { responderMock } from "@/services/mocks/adapter";
import { ApiError } from "@/lib/http/errors";

export interface ResultadoUpload {
  arquivo: string;
  linhasLidas: number;
  linhasIgnoradas: number;
  duplicado: boolean;
}

const EXTENSOES_ACEITAS = [".xlsx", ".xls"];
const TAMANHO_MAXIMO_BYTES = 50 * 1024 * 1024;

export function validarArquivo(arquivo: File): string | null {
  const nome = arquivo.name.toLowerCase();
  if (!EXTENSOES_ACEITAS.some((extensao) => nome.endsWith(extensao))) {
    return "Envie uma planilha do Excel (.xlsx). Outros formatos não são aceitos.";
  }
  if (arquivo.size > TAMANHO_MAXIMO_BYTES) {
    return "O arquivo passa de 50 MB. Divida a planilha em partes menores.";
  }
  if (arquivo.size === 0) {
    return "O arquivo está vazio.";
  }
  return null;
}

export async function enviarPlanilha(arquivo: File, signal?: AbortSignal): Promise<ResultadoUpload> {
  if (env.useMocks) {
    return responderMock(
      { arquivo: arquivo.name, linhasLidas: 3_284, linhasIgnoradas: 12, duplicado: false },
      signal,
    );
  }

  const formData = new FormData();
  formData.append("file", arquivo);

  try {
    const resposta = await request<{ filename: string; rows_processed: number; rows_skipped: number }>(
      "/api/v1/upload",
      { method: "POST", formData, ...(signal ? { signal } : {}) },
    );
    return {
      arquivo: resposta.filename,
      linhasLidas: resposta.rows_processed,
      linhasIgnoradas: resposta.rows_skipped,
      duplicado: false,
    };
  } catch (erro) {
    if (erro instanceof ApiError && erro.status === 409) {
      return { arquivo: arquivo.name, linhasLidas: 0, linhasIgnoradas: 0, duplicado: true };
    }
    throw erro;
  }
}

export async function dispararRetrain(signal?: AbortSignal): Promise<void> {
  if (env.useMocks) {
    await responderMock(undefined, signal);
    return;
  }
  await request<void>("/api/v1/models/retrain", { method: "POST", ...(signal ? { signal } : {}) });
}
