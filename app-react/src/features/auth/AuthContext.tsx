import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { mensagemDoErro } from "@/lib/http/errors";
import { tokenStore } from "@/lib/http/tokenStore";
import type { Perfil, Usuario } from "@/domain/types";
import * as authApi from "./api";

interface AuthContextValue {
  usuario: Usuario | null;
  autenticado: boolean;
  inicializando: boolean;
  entrando: boolean;
  erro: string | null;
  entrar: (email: string, senha: string) => Promise<boolean>;
  sair: () => void;
  temPerfil: (perfil: Perfil) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [inicializando, setInicializando] = useState(true);
  const [entrando, setEntrando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;

    if (!tokenStore.getRefreshToken()) {
      setInicializando(false);
      return;
    }

    authApi
      .buscarUsuarioAtual()
      .then((dados) => ativo && setUsuario(dados))
      .catch(() => tokenStore.limpar())
      .finally(() => ativo && setInicializando(false));

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(
    () =>
      tokenStore.subscribe(() => {
        if (!tokenStore.getAccessToken() && !tokenStore.getRefreshToken()) setUsuario(null);
      }),
    [],
  );

  const entrar = useCallback(async (email: string, senha: string): Promise<boolean> => {
    setEntrando(true);
    setErro(null);
    try {
      setUsuario(await authApi.login(email, senha));
      return true;
    } catch (causa) {
      setErro(mensagemDoErro(causa));
      return false;
    } finally {
      setEntrando(false);
    }
  }, []);

  const sair = useCallback(() => {
    authApi.logout();
    setUsuario(null);
  }, []);

  const valor = useMemo<AuthContextValue>(
    () => ({
      usuario,
      autenticado: usuario !== null,
      inicializando,
      entrando,
      erro,
      entrar,
      sair,
      temPerfil: (perfil) => usuario?.perfil === "admin" || usuario?.perfil === perfil,
    }),
    [usuario, inicializando, entrando, erro, entrar, sair],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth precisa estar dentro de <AuthProvider>.");
  return contexto;
}
