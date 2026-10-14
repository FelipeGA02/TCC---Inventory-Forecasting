/**
 * Análises descritivas da base de vendas (painel inicial). Sem previsão.
 *
 * `analises.json` é gerado por
 *   python -m training_scripts.frontend_mock.gerar_analises_frontend   (em ia-predictor/)
 * em poucos segundos, separado de `baseReal.json` (previsões).
 */
import bruto from "./analises.json";
import type { CategoriaId, FiltroUnidade, UnidadeId } from "@/domain/types";

export type CategoriaAnalise = CategoriaId | "flores-de-corte";

export interface Agregado {
  notas: number;
  volume: number;
  faturamento: number;
}

export interface MesAnalise extends Agregado {
  mes: string;
  volume_encomendas: number;
  faturamento_encomendas: number;
  categorias: Record<CategoriaAnalise, number>;
}

export interface DiaSemanaAnalise {
  dia: string;
  dias_abertos: number;
  fechado: boolean;
  volume_medio: number;
  faturamento_medio: number;
  notas_medias: number;
}

export interface ProdutoTop extends Agregado {
  codigo: string;
  nome: string;
  categoria: CategoriaAnalise;
}

export interface AnaliseUnidade {
  periodo: { inicio: string; fim: string; inicio_ultimo_ano: string };
  resumo: Agregado & { linhas: number; produtos: number; encomendas: Agregado; sem_encomendas: Agregado };
  categorias: Record<CategoriaAnalise, Agregado & { produtos: number }>;
  mensal: MesAnalise[];
  dia_semana: DiaSemanaAnalise[];
  tipo_cliente: { consumidor: Agregado; cadastrado: Agregado };
  pagamento: { forma: string; faturamento: number; notas: number }[];
  top_volume: ProdutoTop[];
  top_faturamento: ProdutoTop[];
}

interface AnalisesJson {
  gerado_em: string;
  limiar_encomenda_un: number;
  unidades: Record<UnidadeId, AnaliseUnidade>;
}

export const analises = bruto as unknown as AnalisesJson;

export const CATEGORIAS_ANALISE: CategoriaAnalise[] = ["grama", "plantas-diversas", "produtos-de-jardim", "flores-de-corte"];
export const COR_FLORES = "#c97b98";

const somar = (v: number[]) => v.reduce((s, x) => s + x, 0);
const somaAgregado = (lista: Agregado[]): Agregado => ({
  notas: somar(lista.map((a) => a.notas)),
  volume: somar(lista.map((a) => a.volume)),
  faturamento: somar(lista.map((a) => a.faturamento)),
});

function lojas(filtro: FiltroUnidade): AnaliseUnidade[] {
  return filtro === "todas" ? Object.values(analises.unidades) : [analises.unidades[filtro]];
}

/** Análises do filtro de loja. Em "Todas", soma as lojas (médias recalculadas a partir das somas). */
export function analiseDe(filtro: FiltroUnidade): AnaliseUnidade {
  const us = lojas(filtro);
  if (us.length === 1) return us[0]!;
  const [a, b] = us as [AnaliseUnidade, AnaliseUnidade];

  const meses = new Map<string, MesAnalise[]>();
  for (const u of us) for (const m of u.mensal) meses.set(m.mes, [...(meses.get(m.mes) ?? []), m]);
  const mensal = [...meses.entries()]
    .sort(([x], [y]) => x.localeCompare(y))
    .map(([mes, lista]) => ({
      mes,
      ...somaAgregado(lista),
      volume_encomendas: somar(lista.map((m) => m.volume_encomendas)),
      faturamento_encomendas: somar(lista.map((m) => m.faturamento_encomendas)),
      categorias: Object.fromEntries(CATEGORIAS_ANALISE.map((c) => [c, somar(lista.map((m) => m.categorias[c]))])) as Record<CategoriaAnalise, number>,
    }));

  // Média por dia aberto: soma das médias das lojas = média da rede no dia (lojas abrem juntas).
  const dia_semana = a.dia_semana.map((d, i) => {
    const e = b.dia_semana[i]!;
    const fechado = d.fechado && e.fechado;
    return {
      dia: d.dia,
      dias_abertos: Math.max(d.dias_abertos, e.dias_abertos),
      fechado,
      volume_medio: fechado ? 0 : d.volume_medio + e.volume_medio,
      faturamento_medio: fechado ? 0 : d.faturamento_medio + e.faturamento_medio,
      notas_medias: fechado ? 0 : d.notas_medias + e.notas_medias,
    };
  });

  const pag = new Map<string, { forma: string; faturamento: number; notas: number }>();
  for (const u of us)
    for (const p of u.pagamento) {
      const atual = pag.get(p.forma) ?? { forma: p.forma, faturamento: 0, notas: 0 };
      pag.set(p.forma, { forma: p.forma, faturamento: atual.faturamento + p.faturamento, notas: atual.notas + p.notas });
    }

  const juntarTop = (chave: "top_volume" | "top_faturamento", ordem: "volume" | "faturamento") => {
    const m = new Map<string, ProdutoTop>();
    for (const u of us)
      for (const p of u[chave]) {
        const atual = m.get(p.codigo);
        m.set(p.codigo, atual ? { ...atual, ...somaAgregado([atual, p]) } : { ...p });
      }
    return [...m.values()].sort((x, y) => y[ordem] - x[ordem]).slice(0, 10);
  };

  return {
    periodo: a.periodo,
    resumo: {
      ...somaAgregado(us.map((u) => u.resumo)),
      linhas: somar(us.map((u) => u.resumo.linhas)),
      produtos: Math.max(...us.map((u) => u.resumo.produtos)),
      encomendas: somaAgregado(us.map((u) => u.resumo.encomendas)),
      sem_encomendas: somaAgregado(us.map((u) => u.resumo.sem_encomendas)),
    },
    categorias: Object.fromEntries(
      CATEGORIAS_ANALISE.map((c) => [c, { ...somaAgregado(us.map((u) => u.categorias[c])), produtos: Math.max(...us.map((u) => u.categorias[c].produtos)) }]),
    ) as AnaliseUnidade["categorias"],
    mensal,
    dia_semana,
    tipo_cliente: {
      consumidor: somaAgregado(us.map((u) => u.tipo_cliente.consumidor)),
      cadastrado: somaAgregado(us.map((u) => u.tipo_cliente.cadastrado)),
    },
    pagamento: [...pag.values()].sort((x, y) => (x.forma === "Outras" ? 1 : y.forma === "Outras" ? -1 : y.faturamento - x.faturamento)),
    top_volume: juntarTop("top_volume", "volume"),
    top_faturamento: juntarTop("top_faturamento", "faturamento"),
  };
}
