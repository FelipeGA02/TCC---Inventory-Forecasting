import { useMemo } from "react";
import { useQuery } from "@/lib/query/useQuery";
import { buscarLinhaDeBase } from "./api";
import { simularCenario, type ParametrosCenario, type ResultadoCenario } from "./model";

export function useSimulacao(produtoId: string, parametros: ParametrosCenario) {
  const { data, carregando, erro, recarregar } = useQuery(
    (signal) => buscarLinhaDeBase(produtoId, signal),
    [produtoId],
  );

  const resultado = useMemo<ResultadoCenario | null>(
    () => (data ? simularCenario(data.base, parametros) : null),
    [data, parametros.descontoPercentual, parametros.complementoId],
  );

  return { carregando, erro, recarregar, produtos: data?.produtos ?? [], resultado };
}
