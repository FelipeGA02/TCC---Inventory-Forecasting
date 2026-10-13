/**
 * Dados do frontend enquanto a API (ia-predictor/openapi.yaml) não está conectada.
 *
 * Nada aqui é inventado: `baseReal.json` é gerado a partir da base real da Verde Perto
 * (jan/2024–fev/2026) por
 *   python -m training_scripts.frontend_mock.gerar_dados_frontend   (em ia-predictor/)
 * — histórico, previsão SARIMAX de 14 dias com IC 95%, desagregação por categoria e
 * produto, validação walk-forward e amostra de registros.
 *
 * Este módulo só tipa o JSON e oferece seletores para o filtro "Todas as lojas".
 */
import bruto from "./baseReal.json";
import type {
  BaseReal,
  CategoriaId,
  DiaHistorico,
  DiaPrevisto,
  FiltroUnidade,
  PorCategoria,
  ProdutoPrevisto,
  SemanaHistorico,
  UnidadeDados,
} from "@/domain/types";

export const dados = bruto as unknown as BaseReal;

export const categorias = dados.categorias;
export const unidades = dados.unidades;
export const HORIZONTE_DIAS = dados.configuracao.horizonte_dias;

/** Paleta categórica validada (dataviz: lightness, chroma, CVD e contraste). Ordem fixa. */
export const CORES_CATEGORIA: PorCategoria<string> = {
  grama: "#1f7a4a",
  "plantas-diversas": "#b8860b",
  "produtos-de-jardim": "#6a5acd",
};

export const IDS_CATEGORIA = categorias.map((c) => c.id) as CategoriaId[];

export function nomeCategoria(id: CategoriaId): string {
  return categorias.find((c) => c.id === id)?.nome ?? id;
}

export function nomeUnidade(filtro: FiltroUnidade): string {
  if (filtro === "todas") return "Todas as lojas";
  return unidades.find((u) => u.id === filtro)?.nome ?? filtro;
}

export function unidadesDoFiltro(filtro: FiltroUnidade): UnidadeDados[] {
  return filtro === "todas" ? unidades : unidades.filter((u) => u.id === filtro);
}

function somaCategorias<T>(itens: T[], pegar: (item: T, c: CategoriaId) => number): PorCategoria<number> {
  const out = {} as PorCategoria<number>;
  for (const c of IDS_CATEGORIA) out[c] = itens.reduce((s, i) => s + pegar(i, c), 0);
  return out;
}

/**
 * Previsão diária do filtro. Para "Todas", soma as lojas dia a dia — inclusive os limites
 * da faixa, o que dá uma faixa conservadora (mais larga que o IC 95% exato da soma).
 */
export function previsaoDe(filtro: FiltroUnidade): DiaPrevisto[] {
  const us = unidadesDoFiltro(filtro);
  const base = us[0]!.previsao;
  return base.map((dia, i) => {
    const dias = us.map((u) => u.previsao[i]!);
    const cats = {} as DiaPrevisto["categorias"];
    for (const c of IDS_CATEGORIA) {
      cats[c] = {
        previsto: dias.reduce((s, d) => s + d.categorias[c].previsto, 0),
        inf: dias.reduce((s, d) => s + d.categorias[c].inf, 0),
        sup: dias.reduce((s, d) => s + d.categorias[c].sup, 0),
      };
    }
    return {
      data: dia.data,
      dia_semana: dia.dia_semana,
      loja_fechada: dias.every((d) => d.loja_fechada),
      evento: dias.map((d) => d.evento).find(Boolean) ?? null,
      previsto: dias.reduce((s, d) => s + d.previsto, 0),
      inf: dias.reduce((s, d) => s + d.inf, 0),
      sup: dias.reduce((s, d) => s + d.sup, 0),
      categorias: cats,
    };
  });
}

export function historicoDiarioDe(filtro: FiltroUnidade): DiaHistorico[] {
  const us = unidadesDoFiltro(filtro);
  return us[0]!.historico_diario.map((dia, i) => {
    const dias = us.map((u) => u.historico_diario[i]!);
    return {
      data: dia.data,
      dia_semana: dia.dia_semana,
      total: dias.reduce((s, d) => s + d.total, 0),
      categorias: somaCategorias(dias, (d, c) => d.categorias[c]),
    };
  });
}

export function historicoSemanalDe(filtro: FiltroUnidade): SemanaHistorico[] {
  const us = unidadesDoFiltro(filtro);
  const semanas = new Map<string, SemanaHistorico[]>();
  for (const u of us) {
    for (const s of u.historico_semanal) {
      semanas.set(s.semana, [...(semanas.get(s.semana) ?? []), s]);
    }
  }
  return [...semanas.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([semana, lista]) => ({
      semana,
      total: lista.reduce((s, x) => s + x.total, 0),
      categorias: somaCategorias(lista, (x, c) => x.categorias[c]),
    }));
}

/**
 * Produtos com previsão detalhada (top 10 por categoria e loja). Em "Todas", o mesmo
 * código vendido nas duas lojas vira uma linha só, com as quantidades somadas.
 */
export function produtosDe(filtro: FiltroUnidade): ProdutoPrevisto[] {
  const us = unidadesDoFiltro(filtro);
  if (us.length === 1) return [...us[0]!.produtos];

  const vendido8 = somaCategorias(historicoDiarioDe(filtro), (d, c) => d.categorias[c]);
  const porCodigo = new Map<string, ProdutoPrevisto>();
  for (const p of us.flatMap((u) => u.produtos)) {
    const atual = porCodigo.get(p.codigo);
    if (!atual) {
      porCodigo.set(p.codigo, { ...p, previsao: p.previsao.map((d) => ({ ...d })) });
      continue;
    }
    atual.vendido_8_semanas += p.vendido_8_semanas;
    atual.vendido_total += p.vendido_total;
    atual.dias_com_venda += p.dias_com_venda;
    atual.vendas += p.vendas;
    atual.previsao_14d += p.previsao_14d;
    atual.historico_semanal = atual.historico_semanal.map((v, i) => v + (p.historico_semanal[i] ?? 0));
    atual.previsao = atual.previsao.map((d, i) => ({
      data: d.data,
      previsto: d.previsto + (p.previsao[i]?.previsto ?? 0),
      inf: d.inf + (p.previsao[i]?.inf ?? 0),
      sup: d.sup + (p.previsao[i]?.sup ?? 0),
    }));
  }
  return [...porCodigo.values()].map((p) => ({
    ...p,
    participacao_categoria: vendido8[p.categoria] ? p.vendido_8_semanas / vendido8[p.categoria] : 0,
  }));
}

/** Segunda-feira da semana de uma data ISO (as semanas do histórico são rotuladas assim). */
export function segundaDaSemana(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  const dow = (d.getDay() + 6) % 7; // 0 = segunda
  d.setDate(d.getDate() - dow);
  return d.toISOString().slice(0, 10);
}

/** Previsão agregada por semana (segunda a domingo), no mesmo formato do histórico. */
export function semanasPrevistasDe(filtro: FiltroUnidade): (SemanaHistorico & { dias: number })[] {
  const grupos = new Map<string, DiaPrevisto[]>();
  for (const d of previsaoDe(filtro)) {
    const s = segundaDaSemana(d.data);
    grupos.set(s, [...(grupos.get(s) ?? []), d]);
  }
  return [...grupos.entries()].map(([semana, dias]) => ({
    semana,
    dias: dias.length,
    total: dias.reduce((s, d) => s + d.previsto, 0),
    categorias: somaCategorias(dias, (d, c) => d.categorias[c].previsto),
  }));
}

/** Soma de uma lista de números. */
export const somar = (valores: number[]): number => valores.reduce((s, v) => s + v, 0);

/** Total previsto nos 14 dias, por categoria. */
export function previsto14dPorCategoria(filtro: FiltroUnidade): PorCategoria<number> {
  return somaCategorias(previsaoDe(filtro), (d, c) => d.categorias[c].previsto);
}
