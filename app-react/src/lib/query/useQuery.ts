import { useCallback, useEffect, useRef, useState } from "react";
import { mensagemDoErro } from "@/lib/http/errors";

export interface QueryResult<T> {
  data: T | undefined;
  carregando: boolean;
  erro: string | null;
  recarregar: () => void;
}

export function useQuery<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): QueryResult<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let ativo = true;

    setCarregando(true);
    setErro(null);

    fetcherRef
      .current(controller.signal)
      .then((resultado) => {
        if (!ativo) return;
        setData(resultado);
        setCarregando(false);
      })
      .catch((causa: unknown) => {
        if (!ativo || controller.signal.aborted) return;
        setErro(mensagemDoErro(causa));
        setCarregando(false);
      });

    return () => {
      ativo = false;
      controller.abort();
    };
  }, [...deps, tick]);

  const recarregar = useCallback(() => setTick((n) => n + 1), []);

  return { data, carregando, erro, recarregar };
}

export interface MutationResult<TArgs extends unknown[], TResult> {
  executar: (...args: TArgs) => Promise<TResult | undefined>;
  emAndamento: boolean;
  erro: string | null;
}

export function useMutation<TArgs extends unknown[], TResult>(
  acao: (...args: TArgs) => Promise<TResult>,
): MutationResult<TArgs, TResult> {
  const [emAndamento, setEmAndamento] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const acaoRef = useRef(acao);
  acaoRef.current = acao;

  const executar = useCallback(async (...args: TArgs): Promise<TResult | undefined> => {
    setEmAndamento(true);
    setErro(null);
    try {
      return await acaoRef.current(...args);
    } catch (causa) {
      setErro(mensagemDoErro(causa));
      return undefined;
    } finally {
      setEmAndamento(false);
    }
  }, []);

  return { executar, emAndamento, erro };
}
