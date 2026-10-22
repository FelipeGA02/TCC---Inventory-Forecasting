/**
 * Sessão do usuário: login em `/auth/login`, renovação em `/auth/refresh` e logout.
 *
 * O token de acesso fica só na memória (`tokenStore`); o de renovação fica no
 * `localStorage` para a sessão sobreviver a um recarregamento da página. Ao abrir o
 * sistema, se houver token de renovação, a sessão é retomada sem pedir a senha. Quando a
 * API recusa a sessão (401 sem renovação possível), o `tokenStore` é limpo e o usuário
 * volta para a tela de login.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Usuario } from "@/domain/types";
import { tokenStore } from "@/lib/http/tokenStore";
import { api, type UsuarioApi } from "../data/api";

interface AuthValor {
  usuario: Usuario | null;
  /** Retomando a sessão salva ao abrir o sistema. */
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  sair: () => void;
}

const AuthContext = createContext<AuthValor | null>(null);

const paraUsuario = (u: UsuarioApi): Usuario => ({ id: u.id, email: u.email, nome: u.name, perfil: u.role });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  // Retoma a sessão salva (token de renovação no navegador).
  useEffect(() => {
    const refresh = tokenStore.getRefreshToken();
    if (!refresh) {
      setCarregando(false);
      return;
    }
    let vivo = true;
    api
      .renovar(refresh)
      .then((t) => {
        tokenStore.setAccessToken(t.access_token, t.expires_in);
        return api.eu();
      })
      .then((u) => vivo && setUsuario(paraUsuario(u)))
      .catch(() => tokenStore.limpar())
      .finally(() => vivo && setCarregando(false));
    return () => {
      vivo = false;
    };
  }, []);

  // Sessão recusada pela API em qualquer tela → volta ao login.
  useEffect(
    () =>
      tokenStore.subscribe(() => {
        if (!tokenStore.getAccessToken() && !tokenStore.getRefreshToken()) setUsuario(null);
      }),
    [],
  );

  const entrar = useCallback(async (email: string, senha: string) => {
    const t = await api.entrar(email.trim(), senha);
    tokenStore.setRefreshToken(t.refresh_token);
    tokenStore.setAccessToken(t.access_token, t.expires_in);
    setUsuario(paraUsuario(await api.eu()));
  }, []);

  const sair = useCallback(() => {
    tokenStore.limpar();
    setUsuario(null);
  }, []);

  const valor = useMemo(() => ({ usuario, carregando, entrar, sair }), [usuario, carregando, entrar, sair]);
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValor {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
