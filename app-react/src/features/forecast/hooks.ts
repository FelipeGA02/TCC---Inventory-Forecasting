import { useQuery, type QueryResult } from "@/lib/query/useQuery";
import type { Produto, Unidade } from "@/domain/types";
import { buscarCatalogo, buscarPrevisao, type ParametrosPrevisao, type Previsao } from "./api";

export function useCatalogo(): QueryResult<{ produtos: Produto[]; unidades: Unidade[] }> {
  return useQuery((signal) => buscarCatalogo(signal), []);
}

export function usePrevisao(parametros: ParametrosPrevisao): QueryResult<Previsao> {
  return useQuery(
    (signal) => buscarPrevisao(parametros, signal),
    [parametros.produtoId, parametros.unidadeId, parametros.horizonte],
  );
}
