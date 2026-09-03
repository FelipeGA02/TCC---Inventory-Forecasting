import { useMemo } from "react";
import { useQuery, type QueryResult } from "@/lib/query/useQuery";
import { compararPorUrgencia, contarPorUrgencia } from "@/domain/urgencia";
import type { AlertaReposicao, Urgencia } from "@/domain/types";
import { buscarAlertas, type FiltroAlertas } from "./api";

export interface AlertasView extends QueryResult<AlertaReposicao[]> {
  alertas: AlertaReposicao[];
  contagem: Record<Urgencia, number>;
}

export function useAlertas(filtro: FiltroAlertas): AlertasView {
  const resultado = useQuery(
    (signal) => buscarAlertas(filtro, signal),
    [filtro.unidade, filtro.grupo],
  );

  const alertas = useMemo(() => {
    const lista = resultado.data ?? [];
    return lista
      .filter(
        (alerta) =>
          (filtro.unidade === "todos" || alerta.unidade === filtro.unidade) &&
          (filtro.grupo === "todos" || alerta.grupo === filtro.grupo),
      )
      .slice()
      .sort(compararPorUrgencia);
  }, [resultado.data, filtro.unidade, filtro.grupo]);

  return { ...resultado, alertas, contagem: contarPorUrgencia(alertas) };
}
