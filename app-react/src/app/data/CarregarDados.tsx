/**
 * Depois do login busca só o contexto do layout (`GET /api/v1/contexto`: lojas, categorias,
 * data da última venda, status dos previsores) — consultas pequenas, sem ler a base. O
 * layout (menu lateral e cabeçalho) aparece na hora; a área da tela mostra a espera até o
 * contexto chegar, e cada tela busca os próprios dados ao abrir (`<Tela>`, `recursos.ts`).
 *
 * `useDados().recarregar()` busca o contexto de novo e descarta os dados das telas; a tela
 * aberta é montada outra vez (`versao`) e busca o que precisa.
 */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Contexto } from "@/domain/types";
import { mensagemDoErro } from "@/lib/http/errors";
import { api } from "./api";
import { definirContexto } from "./painel";
import { invalidarRecursos } from "./recursos";

interface DadosValor {
  contexto: Contexto | null;
  erro: string | null;
  /** Muda a cada recarga: a área da tela usa como `key` para montar a tela de novo. */
  versao: number;
  recarregar: () => Promise<void>;
  tentarDeNovo: () => void;
  atualizando: boolean;
}

const DadosContext = createContext<DadosValor | null>(null);

export function CarregarDados({ children }: { children: ReactNode }) {
  const [contexto, setContexto] = useState<Contexto | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [atualizando, setAtualizando] = useState(false);

  const buscar = useCallback(async () => {
    const c = await api.contexto();
    definirContexto(c);
    setContexto(c);
  }, []);

  const tentarDeNovo = useCallback(() => {
    setErro(null);
    buscar().catch((e: unknown) => setErro(mensagemDoErro(e)));
  }, [buscar]);

  useEffect(tentarDeNovo, [tentarDeNovo]);

  const recarregar = useCallback(async () => {
    setAtualizando(true);
    try {
      await buscar();
      invalidarRecursos();
      setVersao((v) => v + 1);
    } finally {
      setAtualizando(false);
    }
  }, [buscar]);

  return (
    <DadosContext.Provider value={{ contexto, erro, versao, recarregar, tentarDeNovo, atualizando }}>
      {children}
    </DadosContext.Provider>
  );
}

export function useDados(): DadosValor {
  const ctx = useContext(DadosContext);
  if (!ctx) throw new Error("useDados precisa estar dentro de <CarregarDados>");
  return ctx;
}
