import { env } from "@/config/env";
import { http, request } from "@/lib/http/client";
import { ApiError } from "@/lib/http/errors";
import { tokenStore } from "@/lib/http/tokenStore";
import { responderMock } from "@/services/mocks/adapter";
import type { Perfil, Usuario } from "@/domain/types";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: Perfil;
  expires_in: number;
}

interface UserOut {
  id: number;
  email: string;
  role: Perfil;
}

const paraUsuario = (dto: UserOut): Usuario => ({
  id: dto.id,
  email: dto.email,
  perfil: dto.role,
});

const USUARIO_MOCK: Usuario = { id: 1, email: "gestora@floricultura.com", perfil: "admin" };

const MOCK_ACCESS_TOKEN = "mock-access-token";
const MOCK_REFRESH_TOKEN = "mock-refresh-token";
const MOCK_EXPIRA_EM_SEGUNDOS = 8 * 60 * 60;

export async function login(email: string, senha: string): Promise<Usuario> {
  if (env.useMocks) {
    if (senha.length < 4) {
      throw new ApiError(401, "E-mail ou senha incorretos.");
    }
    tokenStore.setAccessToken(MOCK_ACCESS_TOKEN, MOCK_EXPIRA_EM_SEGUNDOS);
    tokenStore.setRefreshToken(MOCK_REFRESH_TOKEN);
    return responderMock({ ...USUARIO_MOCK, email });
  }

  const resposta = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password: senha },
    publica: true,
  });

  tokenStore.setAccessToken(resposta.access_token, resposta.expires_in);
  tokenStore.setRefreshToken(resposta.refresh_token);

  return buscarUsuarioAtual();
}

export async function buscarUsuarioAtual(): Promise<Usuario> {
  if (env.useMocks) {
    tokenStore.setAccessToken(MOCK_ACCESS_TOKEN, MOCK_EXPIRA_EM_SEGUNDOS);
    return responderMock(USUARIO_MOCK);
  }
  return paraUsuario(await http.get<UserOut>("/auth/me"));
}

export function logout(): void {
  tokenStore.limpar();
}
