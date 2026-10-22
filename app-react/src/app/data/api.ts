/**
 * Chamadas à API (`ia-predictor/openapi.yaml`) usadas pelas telas. O token vai pelo
 * cliente HTTP (`@/lib/http/client`), que renova o acesso sozinho quando expira.
 */
import { http } from "@/lib/http/client";
import type { BaseReal, Contexto, DiaBacktest, Perfil } from "@/domain/types";
import type { AnalisesJson } from "./analises";

export interface UsuarioApi {
  id: number;
  email: string;
  name: string;
  role: Perfil;
}

export interface TokenApi {
  access_token: string;
  refresh_token: string;
  role: Perfil;
  expires_in: number;
}

export interface ResultadoUpload {
  filename: string;
  rows_added: number;
  rows_skipped: number;
  rows_duplicate: number;
  processing_time_seconds: number;
  retrain_scheduled: boolean;
  /** início do treino automático após o upload; nulo = fica para o treino semanal */
  retrain_at: string | null;
  errors: string[];
}

export interface StatusModelos {
  last_retrain_at: string | null;
  next_retrain_at: string | null;
  forecast_until: string | null;
  is_training: boolean;
  last_retrain_summary: string | null;
}

/** Filtros, ordem e página da tela Conferir Dados (query de `/api/v1/registros/*`). */
export type ConsultaRegistros = Record<string, string | number | null | undefined | string[]>;

export const api = {
  entrar: (email: string, password: string) =>
    http.post<TokenApi>("/auth/login", { email, password }, { publica: true }),
  renovar: (refresh_token: string) =>
    http.post<{ access_token: string; expires_in: number }>("/auth/refresh", { refresh_token }, { publica: true }),
  eu: () => http.get<UsuarioApi>("/auth/me"),

  contexto: () => http.get<Contexto>("/api/v1/contexto"),
  painel: () => http.get<BaseReal>("/api/v1/painel"),
  backtestProduto: (loja: string, codigo: string) =>
    http.get<DiaBacktest[]>(`/api/v1/painel/produtos/${encodeURIComponent(loja)}/${encodeURIComponent(codigo)}/backtest`),
  analises: () => http.get<AnalisesJson>("/api/v1/analises"),

  // Conferir Dados: a base paginada no banco
  indiceRegistros: <T>() => http.get<T>("/api/v1/registros"),
  linhasRegistros: <T>(query: ConsultaRegistros, signal?: AbortSignal) =>
    http.get<T>("/api/v1/registros/linhas", { query, ...(signal ? { signal } : {}) }),
  resumoRegistros: <T>(query: ConsultaRegistros, signal?: AbortSignal) =>
    http.get<T>("/api/v1/registros/resumo", { query, ...(signal ? { signal } : {}) }),
  itensDaNota: <T>(loja: string, data: string, nota: string) =>
    http.get<T>("/api/v1/registros/nota", { query: { loja, data, nota } }),
  exportarRegistros: <T>(query: ConsultaRegistros) => http.get<T>("/api/v1/registros/exportar", { query }),

  enviarPlanilha: (arquivo: File) => {
    const formData = new FormData();
    formData.append("file", arquivo);
    return http.post<ResultadoUpload>("/api/v1/upload", undefined, { formData });
  },
  statusModelos: () => http.get<StatusModelos>("/api/v1/models/status"),
  atualizarModelos: () => http.post<{ message: string; started_at: string }>("/api/v1/models/retrain"),
};
