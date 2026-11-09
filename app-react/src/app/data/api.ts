/**
 * Chamadas à API (`ia-predictor/openapi.yaml`) usadas pelas telas. O token vai pelo
 * cliente HTTP (`@/lib/http/client`), que renova o acesso sozinho quando expira.
 */
import { http } from "@/lib/http/client";
import type { BaseReal, Contexto, HistoricoPrevisao, Perfil } from "@/domain/types";
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
  /** Venda nova: a previsão só a usa depois de "Treinar previsões" (o treino não roda sozinho). */
  needs_training: boolean;
  errors: string[];
}

/** Conferência da planilha antes de gravar (`POST /api/v1/upload/verificacao`): nada é gravado. */
export interface VerificacaoUpload {
  filename: string;
  period_start: string;
  period_end: string;
  rows_new: number;
  rows_duplicate: number;
  rows_skipped: number;
  units: { unit_id: string; unit_name: string; first_day: string; last_day: string; rows: number; last_day_loaded: string | null }[];
  /** Lojas com dia de loja aberta que ficaria sem venda na base; `message` é o aviso pronto. */
  missing_days: { unit_id: string; unit_name: string; days: number; ranges: { start: string; end: string }[]; message: string }[];
  /** Avisos da leitura (linhas ignoradas). */
  warnings: string[];
}

/** Serviço de previsão (`/api/v1/servico-previsao/*`, só admin). */
export type StatusTreino = "pending" | "running" | "done" | "error" | "skipped";

export interface TreinoServico {
  id: number;
  status: StatusTreino;
  criado_em: string;
  iniciado_em: string | null;
  concluido_em: string | null;
  dados_ate: string | null;
  total_series: number;
  series_concluidas: number;
  progresso_pct: number;
  serie_atual: string | null;
  series_treinadas: number;
  series_dados_insuficientes: number;
  series_com_erro: number;
  mensagem: string | null;
}

export interface StatusServicoPrevisao {
  treino_na_api: boolean;
  em_andamento: TreinoServico | null;
  ultimo: TreinoServico | null;
  ultimo_concluido_em: string | null;
  /** se um disparo agora treinaria; nulo enquanto há treino em andamento */
  dados_alterados: boolean | null;
  config: {
    m: number;
    d: number;
    /** d testados no walk-forward de cada série; fica o que errou menos (ADR-020) */
    d_candidatos: number[];
    D: number;
    janela_dias: number;
    origens: number;
    passo_dias: number;
    /** horizonte do teste de acerto (walk-forward) */
    horizonte_dias: number;
    /** dias da previsão gravada (ADR-021) */
    horizonte_previsao_dias: number;
    base: string;
    categoria_produtos: string;
  };
}

export interface DisparoTreino {
  iniciado: boolean;
  mensagem: string;
  treino: TreinoServico;
}

/** Filtros, ordem e página da tela Conferir Dados (query de `/api/v1/registros/*`). */
export type ConsultaRegistros = Record<string, string | number | null | undefined | string[]>;

export const api = {
  entrar: (email: string, password: string) =>
    http.post<TokenApi>("/auth/login", { email, password }, { publica: true }),
  renovar: (refresh_token: string) =>
    http.post<{ access_token: string; expires_in: number }>("/auth/refresh", { refresh_token }, { publica: true }),
  sair: (refresh_token: string) => http.post<void>("/auth/logout", { refresh_token }, { publica: true }),
  eu: () => http.get<UsuarioApi>("/auth/me"),

  contexto: () => http.get<Contexto>("/api/v1/contexto"),
  painel: () => http.get<BaseReal>("/api/v1/painel"),
  historico: (loja: string, nivel: "categoria" | "produto", item: string) =>
    http.get<HistoricoPrevisao>(
      `/api/v1/painel/historico/${encodeURIComponent(loja)}/${nivel}/${encodeURIComponent(item)}`,
    ),
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

  verificarPlanilha: (arquivo: File) => {
    const formData = new FormData();
    formData.append("file", arquivo);
    return http.post<VerificacaoUpload>("/api/v1/upload/verificacao", undefined, { formData });
  },
  enviarPlanilha: (arquivo: File) => {
    const formData = new FormData();
    formData.append("file", arquivo);
    return http.post<ResultadoUpload>("/api/v1/upload", undefined, { formData });
  },

  statusServicoPrevisao: () => http.get<StatusServicoPrevisao>("/api/v1/servico-previsao/status"),
  treinarPrevisoes: () => http.post<DisparoTreino>("/api/v1/servico-previsao/treinos"),
};
