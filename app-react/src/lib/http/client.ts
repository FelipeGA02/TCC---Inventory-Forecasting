import { env } from "@/config/env";
import { ApiError, NetworkError, mensagemPara } from "./errors";
import { tokenStore } from "./tokenStore";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  /** Listas viram o parâmetro repetido (`?lojas=a&lojas=b`). */
  query?: Record<string, string | number | boolean | undefined | null | (string | number)[]>;
  signal?: AbortSignal;
  publica?: boolean;
  blob?: boolean;
}

function montarUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(env.apiBaseUrl + path);
  if (query) {
    for (const [chave, valor] of Object.entries(query)) {
      if (Array.isArray(valor)) for (const v of valor) url.searchParams.append(chave, String(v));
      else if (valor !== undefined && valor !== null && valor !== "") url.searchParams.set(chave, String(valor));
    }
  }
  return url.toString();
}

let refreshEmVoo: Promise<boolean> | null = null;

async function renovarAccessToken(): Promise<boolean> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return false;

  refreshEmVoo ??= (async () => {
    try {
      const resposta = await fetch(montarUrl("/auth/refresh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resposta.ok) {
        tokenStore.limpar();
        return false;
      }
      const dados = (await resposta.json()) as { access_token: string; expires_in: number };
      tokenStore.setAccessToken(dados.access_token, dados.expires_in);
      return true;
    } catch {
      return false;
    } finally {
      refreshEmVoo = null;
    }
  })();

  return refreshEmVoo;
}

async function executar(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};

  if (!options.publica) {
    const token = tokenStore.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const init: RequestInit = { method: options.method ?? "GET", headers };
  if (body !== undefined) init.body = body;
  if (options.signal) init.signal = options.signal;

  return fetch(montarUrl(path, options.query), init);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let resposta: Response;

  try {
    resposta = await executar(path, options);

    if (resposta.status === 401 && !options.publica) {
      const renovou = await renovarAccessToken();
      if (renovou) resposta = await executar(path, options);
    }
  } catch (erro) {
    if (erro instanceof DOMException && erro.name === "AbortError") throw erro;
    throw new NetworkError(erro);
  }

  if (!resposta.ok) {
    if (resposta.status === 401) tokenStore.limpar();
    const detail = await resposta
      .json()
      .then((corpo: { detail?: string }) => corpo.detail)
      .catch(() => undefined);
    throw new ApiError(resposta.status, mensagemPara(resposta.status), detail);
  }

  if (options.blob) return (await resposta.blob()) as T;
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

export const http = {
  get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "POST", body }),
};
