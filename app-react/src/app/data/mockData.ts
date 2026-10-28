/**
 * Painel de previsão vindo da API (`GET /api/v1/painel`, formato `BaseReal`): previsão das
 * 4 categorias e dos produtos de grama de cada loja (o total da loja é a soma das
 * categorias), histórico, encomendas grandes e testes de acerto, montados no backend a partir das
 * vendas do banco e do último treino concluído.
 *
 * Carregado em duas partes, por isso os valores abaixo são `let` (o import do ES module
 * enxerga o valor atual):
 *   - `definirContexto()` (logo após o login, `GET /api/v1/contexto`): lojas, categorias e
 *     configuração — o que o layout e os filtros usam;
 *   - `definirPainel()` (só quando uma tela que usa a previsão é aberta, ver `recursos.ts`):
 *     o painel inteiro em `dados` e `unidades`.
 * Este módulo oferece os seletores para os filtros de loja e categoria.
 */
import type {
  BaseReal,
  Categoria,
  CategoriaId,
  Contexto,
  DiaHistorico,
  DiaPrevisto,
  Faixa,
  FiltroCategoria,
  FiltroUnidade,
  PorCategoria,
  ProdutoDaLoja,
  SemanaHistorico,
  UnidadeDados,
} from "@/domain/types";

export let contexto: Contexto;
export let lojas: Contexto["lojas"];
export let categorias: Categoria[];
export let HORIZONTE_DIAS: number;
export let LIMIAR_ENCOMENDA: number;
export let IDS_CATEGORIA: CategoriaId[];

export let dados: BaseReal;
export let unidades: UnidadeDados[];

export function definirContexto(c: Contexto): void {
  contexto = c;
  lojas = c.lojas;
  categorias = c.categorias;
  HORIZONTE_DIAS = c.configuracao.horizonte_dias;
  LIMIAR_ENCOMENDA = c.configuracao.limiar_encomenda_un;
  IDS_CATEGORIA = c.categorias.map((x) => x.id);
}

export function definirPainel(painel: BaseReal): void {
  dados = painel;
  unidades = painel.unidades;
}

/** Paleta categórica validada (dataviz: lightness, chroma, CVD e contraste). Ordem fixa. */
export const CORES_CATEGORIA: PorCategoria<string> = {
  grama: "#1f7a4a",
  "plantas-diversas": "#b8860b",
  "produtos-de-jardim": "#6a5acd",
  "flores-de-corte": "#c97b98",
};
/** Encomendas grandes: neutro, para não competir com as categorias. */
export const COR_ENCOMENDA = "#9aa4b1";
export const COR_TOTAL = "#1a6b3c";

export function nomeCategoria(id: CategoriaId | "todas"): string {
  if (id === "todas") return "Todas as categorias";
  return categorias.find((c) => c.id === id)?.nome ?? id;
}

export function corCategoria(id: FiltroCategoria): string {
  return id === "todas" ? COR_TOTAL : CORES_CATEGORIA[id];
}

export function nomeUnidade(filtro: FiltroUnidade): string {
  if (filtro === "todas") return "Todas as lojas";
  return lojas.find((u) => u.id === filtro)?.nome ?? filtro;
}

export function unidadesDoFiltro(filtro: FiltroUnidade): UnidadeDados[] {
  return filtro === "todas" ? unidades : unidades.filter((u) => u.id === filtro);
}

/** Soma de uma lista de números. */
export const somar = (valores: number[]): number => valores.reduce((s, v) => s + v, 0);

function somaCategorias<T>(itens: T[], pegar: (item: T, c: CategoriaId) => number): PorCategoria<number> {
  const out = {} as PorCategoria<number>;
  for (const c of IDS_CATEGORIA) out[c] = somar(itens.map((i) => pegar(i, c)));
  return out;
}

// ---------------------------------------------------------------------------
// Previsão e histórico (loja → categoria)
// ---------------------------------------------------------------------------

/**
 * Previsão diária do filtro de loja. Em "Todas", soma as lojas dia a dia — inclusive os
 * limites da faixa, o que dá uma faixa conservadora (mais larga que a exata da soma).
 */
export function previsaoDe(filtro: FiltroUnidade): DiaPrevisto[] {
  const us = unidadesDoFiltro(filtro);
  return us[0]!.previsao.map((dia, i) => {
    const dias = us.map((u) => u.previsao[i]!);
    const cats = {} as DiaPrevisto["categorias"];
    for (const c of IDS_CATEGORIA) {
      cats[c] = {
        previsto: somar(dias.map((d) => d.categorias[c].previsto)),
        inf: somar(dias.map((d) => d.categorias[c].inf)),
        sup: somar(dias.map((d) => d.categorias[c].sup)),
      };
    }
    return {
      data: dia.data,
      dia_semana: dia.dia_semana,
      loja_fechada: dias.every((d) => d.loja_fechada),
      evento: dias.map((d) => d.evento).find(Boolean) ?? null,
      previsto: somar(dias.map((d) => d.previsto)),
      inf: somar(dias.map((d) => d.inf)),
      sup: somar(dias.map((d) => d.sup)),
      categorias: cats,
    };
  });
}

/** Faixa do dia para o filtro de categoria ("todas" = soma das 3 categorias). */
export function faixaDoDia(dia: DiaPrevisto, categoria: FiltroCategoria): Faixa {
  return categoria === "todas" ? dia : dia.categorias[categoria];
}

/** Venda (sem encomendas grandes) de um dia/semana do histórico para o filtro de categoria. */
export function vendaDe(item: { total: number; categorias: PorCategoria<number> }, categoria: FiltroCategoria): number {
  return categoria === "todas" ? item.total : item.categorias[categoria];
}

export function historicoDiarioDe(filtro: FiltroUnidade): DiaHistorico[] {
  const us = unidadesDoFiltro(filtro);
  return us[0]!.historico_diario.map((dia, i) => {
    const dias = us.map((u) => u.historico_diario[i]!);
    return {
      data: dia.data,
      dia_semana: dia.dia_semana,
      total: somar(dias.map((d) => d.total)),
      encomendas: somar(dias.map((d) => d.encomendas)),
      categorias: somaCategorias(dias, (d, c) => d.categorias[c]),
    };
  });
}

export function historicoSemanalDe(filtro: FiltroUnidade): SemanaHistorico[] {
  const semanas = new Map<string, SemanaHistorico[]>();
  for (const u of unidadesDoFiltro(filtro)) {
    for (const s of u.historico_semanal) semanas.set(s.semana, [...(semanas.get(s.semana) ?? []), s]);
  }
  return [...semanas.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([semana, lista]) => ({
      semana,
      total: somar(lista.map((x) => x.total)),
      encomendas: somar(lista.map((x) => x.encomendas)),
      categorias: somaCategorias(lista, (x, c) => x.categorias[c]),
    }));
}

/** Segunda-feira da semana de uma data ISO (as semanas do histórico são rotuladas assim). */
export function segundaDaSemana(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

/** Previsão agregada por semana (segunda a domingo), no formato do histórico. */
export function semanasPrevistasDe(filtro: FiltroUnidade): (SemanaHistorico & { dias: number })[] {
  const grupos = new Map<string, DiaPrevisto[]>();
  for (const d of previsaoDe(filtro)) {
    const s = segundaDaSemana(d.data);
    grupos.set(s, [...(grupos.get(s) ?? []), d]);
  }
  return [...grupos.entries()].map(([semana, dias]) => ({
    semana,
    dias: dias.length,
    total: somar(dias.map((d) => d.previsto)),
    encomendas: 0,
    categorias: somaCategorias(dias, (d, c) => d.categorias[c].previsto),
  }));
}

// ---------------------------------------------------------------------------
// Produtos
// ---------------------------------------------------------------------------

/** O produto tem previsão neste treino (os de grama que vendem pouco ficam só com o motivo). */
export const temPrevisao = (p: { previsao: unknown[] }): boolean => p.previsao.length > 0;

/**
 * Produtos de grama do filtro, cada um com o modelo da sua loja. Em "Todas as lojas" cada
 * produto aparece por loja (o mesmo código pode ter previsão numa loja e não na outra).
 * Ordem: os com previsão pela previsão de 14 dias, depois os outros pela venda das 8 semanas.
 */
export function produtosDe(
  filtro: FiltroUnidade,
  categoria: FiltroCategoria = "todas",
  somenteComPrevisao = false,
): ProdutoDaLoja[] {
  return unidadesDoFiltro(filtro)
    .flatMap((u) => u.produtos.map((p) => ({ ...p, unidade: u.id, nomeUnidade: u.nome })))
    .filter((p) => categoria === "todas" || p.categoria === categoria)
    .filter((p) => !somenteComPrevisao || temPrevisao(p))
    .sort((a, b) =>
      temPrevisao(a) !== temPrevisao(b)
        ? temPrevisao(a) ? -1 : 1
        : temPrevisao(a)
          ? (b.previsao_14d ?? 0) - (a.previsao_14d ?? 0)
          : b.vendido_8_semanas - a.vendido_8_semanas,
    );
}

/** Total previsto nos 14 dias para o filtro de categoria. */
export function previsto14d(filtro: FiltroUnidade, categoria: FiltroCategoria = "todas"): Faixa {
  const dias = previsaoDe(filtro).map((d) => faixaDoDia(d, categoria));
  return { previsto: somar(dias.map((d) => d.previsto)), inf: somar(dias.map((d) => d.inf)), sup: somar(dias.map((d) => d.sup)) };
}

// ---------------------------------------------------------------------------
// Encomendas grandes (fora da previsão)
// ---------------------------------------------------------------------------

export function encomendasDe(filtro: FiltroUnidade) {
  const us = unidadesDoFiltro(filtro);
  return {
    vendas: somar(us.map((u) => u.encomendas.vendas)),
    volume: somar(us.map((u) => u.encomendas.volume)),
    pctVolume: somar(us.map((u) => u.encomendas.volume)) /
      somar(us.map((u) => u.encomendas.volume / (u.encomendas.pct_volume / 100))) * 100,
    ultimas: us
      .flatMap((u) => u.encomendas.ultimas.map((e) => ({ ...e, loja: u.nome })))
      .sort((a, b) => b.data.localeCompare(a.data)),
  };
}
