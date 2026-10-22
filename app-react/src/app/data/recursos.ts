/**
 * Dados pesados das telas, buscados só quando uma tela que precisa deles é aberta (e
 * guardados até o próximo "Atualizar"): o painel de previsão e as análises descritivas.
 * O contexto do layout vem antes, em `CarregarDados`; a base linha a linha (Conferir Dados)
 * é paginada no banco e não passa por aqui.
 */
import { definirAnalises } from "./analises";
import { api } from "./api";
import { definirPainel } from "./mockData";

export type Recurso = "painel" | "analises";

const BUSCAR: Record<Recurso, () => Promise<void>> = {
  painel: () => api.painel().then(definirPainel),
  analises: () => api.analises().then(definirAnalises),
};

const prontos = new Set<Recurso>();
const emAndamento = new Map<Recurso, Promise<void>>();

export function estaoProntos(recursos: Recurso[]): boolean {
  return recursos.every((r) => prontos.has(r));
}

/** Busca o que ainda não chegou; duas telas pedindo o mesmo recurso esperam a mesma busca. */
export function garantir(recursos: Recurso[]): Promise<void> {
  return Promise.all(
    recursos
      .filter((r) => !prontos.has(r))
      .map((r) => {
        let busca = emAndamento.get(r);
        if (!busca) {
          busca = BUSCAR[r]()
            .then(() => {
              prontos.add(r);
            })
            .finally(() => emAndamento.delete(r));
          emAndamento.set(r, busca);
        }
        return busca;
      }),
  ).then(() => undefined);
}

/** Depois de carregar uma planilha ou de "Atualizar": a próxima tela aberta busca de novo. */
export function invalidarRecursos(): void {
  prontos.clear();
}
