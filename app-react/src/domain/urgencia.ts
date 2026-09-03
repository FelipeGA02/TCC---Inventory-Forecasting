import type { AlertaReposicao, Urgencia } from "./types";

const ORDEM: Record<Urgencia, number> = { critico: 0, atencao: 1, ok: 2 };

export function compararPorUrgencia(a: { urgencia: Urgencia }, b: { urgencia: Urgencia }): number {
  return ORDEM[a.urgencia] - ORDEM[b.urgencia];
}

export function contarPorUrgencia<T extends { urgencia: Urgencia }>(
  itens: readonly T[],
): Record<Urgencia, number> {
  return itens.reduce<Record<Urgencia, number>>(
    (acumulado, item) => {
      acumulado[item.urgencia] += 1;
      return acumulado;
    },
    { critico: 0, atencao: 0, ok: 0 },
  );
}

export function coberturaDeEstoque(alerta: AlertaReposicao): number {
  if (alerta.estoqueMinimo <= 0) return 1;
  return Math.min(1, alerta.estoqueAtual / alerta.estoqueMinimo);
}
