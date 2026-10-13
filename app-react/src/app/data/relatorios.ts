/**
 * Catálogo de relatórios para download. Cada relatório monta uma tabela a partir dos dados
 * reais (`mockData`) e dos filtros escolhidos; a tela decide o formato (XLSX, CSV ou PDF).
 */
import type { CategoriaId, FiltroUnidade } from "@/domain/types";
import { estiloStatus } from "@/styles/tokens";
import { formatarData, formatarDecimal, formatarDiaMes, formatarNumero, formatarPercentual, formatarQtd } from "@/lib/format";
import { tabelaHtml, type Celula, type Tabela, type TipoColuna } from "@/lib/exportar";
import {
  HORIZONTE_DIAS,
  IDS_CATEGORIA,
  categorias,
  dados,
  nomeCategoria,
  nomeUnidade,
  previsaoDe,
  produtosDe,
  somar,
  unidadesDoFiltro,
} from "./mockData";

export type Formato = "xlsx" | "csv" | "pdf";
export type FiltroCategoria = CategoriaId | "todas";

export interface FiltrosRelatorio {
  unidade: FiltroUnidade;
  categoria: FiltroCategoria;
}

export type GrupoRelatorio = "Previsão" | "Histórico de vendas" | "Qualidade da previsão" | "Base de dados";

export interface Relatorio {
  id: string;
  grupo: GrupoRelatorio;
  titulo: string;
  descricao: string;
  /** Para que a loja usa este relatório. */
  uso: string;
  filtros: ("unidade" | "categoria")[];
  formatos: Formato[];
  gerar: (f: FiltrosRelatorio) => Tabela;
  /** Relatório só em PDF, com layout próprio (não é uma tabela única). */
  html?: (f: FiltrosRelatorio) => string;
}

const cats = (f: FiltrosRelatorio): CategoriaId[] => (f.categoria === "todas" ? IDS_CATEGORIA : [f.categoria]);
const r1 = (v: number) => Math.round(v * 10) / 10;

export function formatarCelula(v: Celula, tipo: TipoColuna): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") return tipo === "decimal" ? formatarDecimal(v) : formatarQtd(v);
  if (tipo === "data") return formatarData(v);
  return v;
}

export const relatorios: Relatorio[] = [
  {
    id: "previsao-diaria",
    grupo: "Previsão",
    titulo: `Previsão diária · próximos ${HORIZONTE_DIAS} dias`,
    descricao: "Venda mais provável e faixa provável (95%) por dia, loja e categoria.",
    uso: "Planejar o recebimento de mercadoria e a equipe de cada dia.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Venda mais provável", tipo: "numero" },
        { titulo: "Mínimo provável", tipo: "numero" },
        { titulo: "Máximo provável", tipo: "numero" },
        { titulo: "Observação", tipo: "texto" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.previsao.flatMap((d) =>
          cats(f).map((c) => [
            d.data,
            d.dia_semana,
            u.nome,
            nomeCategoria(c),
            d.categorias[c].previsto,
            d.categorias[c].inf,
            d.categorias[c].sup,
            [d.loja_fechada ? "Loja fechada" : "", d.evento ?? ""].filter(Boolean).join(" · "),
          ]),
        ),
      ),
    }),
  },
  {
    id: "previsao-produtos",
    grupo: "Previsão",
    titulo: "Previsão por produto",
    descricao: `Os 10 produtos de maior venda em cada categoria, com o total previsto e a previsão de cada um dos ${HORIZONTE_DIAS} dias.`,
    uso: "Conferir o volume esperado dos itens que mais giram antes de fazer o pedido.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => {
      const dias = previsaoDe(f.unidade).map((d) => d.data);
      const linhas: Celula[][] = [];
      for (const u of unidadesDoFiltro(f.unidade)) {
        for (const p of u.produtos.filter((p) => cats(f).includes(p.categoria)).sort((a, b) => b.previsao_14d - a.previsao_14d)) {
          linhas.push([
            u.nome,
            p.codigo,
            p.nome,
            nomeCategoria(p.categoria),
            p.subcategoria,
            r1(p.participacao_categoria * 100),
            p.vendido_8_semanas,
            p.previsao_14d,
            ...p.previsao.map((d) => d.previsto),
          ]);
        }
      }
      return {
        colunas: [
          { titulo: "Loja", tipo: "texto" },
          { titulo: "Código", tipo: "texto" },
          { titulo: "Produto", tipo: "texto" },
          { titulo: "Categoria", tipo: "texto" },
          { titulo: "Tipo", tipo: "texto" },
          { titulo: "Parte da categoria (%)", tipo: "numero" },
          { titulo: "Vendido 8 semanas", tipo: "numero" },
          { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
          ...dias.map((d) => ({ titulo: formatarDiaMes(d), tipo: "numero" as const })),
        ],
        linhas,
      };
    },
  },
  {
    id: "vendas-semanais",
    grupo: "Histórico de vendas",
    titulo: "Vendas por semana · base completa",
    descricao: `Quantidade vendida por semana e categoria, de ${formatarData(dados.base.inicio)} a ${formatarData(dados.base.fim)}.`,
    uso: "Comparar com o mesmo período do ano anterior e ver a sazonalidade.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Semana (segunda)", tipo: "data" },
        { titulo: "Loja", tipo: "texto" },
        ...cats(f).map((c) => ({ titulo: nomeCategoria(c), tipo: "numero" as const })),
        { titulo: "Total", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.historico_semanal.map((s) => [
          s.semana,
          u.nome,
          ...cats(f).map((c) => s.categorias[c]),
          r1(somar(cats(f).map((c) => s.categorias[c]))),
        ]),
      ),
    }),
  },
  {
    id: "vendas-diarias",
    grupo: "Histórico de vendas",
    titulo: "Vendas por dia · últimas 8 semanas",
    descricao: "O histórico recente usado para repartir a previsão entre as categorias.",
    uso: "Conferir o movimento recente dia a dia.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        ...cats(f).map((c) => ({ titulo: nomeCategoria(c), tipo: "numero" as const })),
        { titulo: "Total", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.historico_diario.map((d) => [
          d.data,
          d.dia_semana,
          u.nome,
          ...cats(f).map((c) => d.categorias[c]),
          r1(somar(cats(f).map((c) => d.categorias[c]))),
        ]),
      ),
    }),
  },
  {
    id: "acerto-resumo",
    grupo: "Qualidade da previsão",
    titulo: "Resumo de acerto por loja",
    descricao: "Indicadores dos testes de acerto (MASE, faixa provável, comparação com a regra simples).",
    uso: "Saber quanto confiar na previsão de cada loja.",
    filtros: ["unidade"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Situação", tipo: "texto" },
        { titulo: "MASE", tipo: "decimal" },
        { titulo: "Erro ÷ regra simples", tipo: "decimal" },
        { titulo: "Dias dentro da faixa (%)", tipo: "numero" },
        { titulo: "Rodadas vencidas", tipo: "texto" },
        { titulo: "Erro médio por dia", tipo: "numero" },
        { titulo: "Largura média da faixa", tipo: "numero" },
        { titulo: "Previsto ÷ vendido (%)", tipo: "numero" },
        { titulo: "Dias testados", tipo: "numero" },
        { titulo: "Modelo", tipo: "texto" },
      ],
      linhas: unidadesDoFiltro(f.unidade).map((u) => {
        const m = u.modelo.metricas;
        return [
          u.nome,
          estiloStatus[u.modelo.status].label,
          m.mase,
          m.erro_relativo_naive,
          m.cobertura_ic95_pct,
          `${m.rodadas_vence_naive} de ${m.rodadas}`,
          m.mae,
          m.largura_ic95,
          m.previsto_sobre_real_pct,
          m.dias_avaliados,
          `SARIMAX(${u.modelo.ordem.join(",")})(${u.modelo.ordem_sazonal.join(",")}) · ${u.modelo.transformacao}`,
        ];
      }),
    }),
  },
  {
    id: "acerto-dias",
    grupo: "Qualidade da previsão",
    titulo: "Testes de acerto · dia a dia",
    descricao: "Cada dia testado: o que o sistema previu, a faixa, o que foi vendido e a regra simples.",
    uso: "Auditar a previsão em datas específicas (feriados, picos de venda).",
    filtros: ["unidade"],
    formatos: ["xlsx", "csv"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Vendido", tipo: "numero" },
        { titulo: "Previsto", tipo: "numero" },
        { titulo: "Mínimo provável", tipo: "numero" },
        { titulo: "Máximo provável", tipo: "numero" },
        { titulo: "Dentro da faixa", tipo: "texto" },
        { titulo: "Regra simples (semana anterior)", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.backtest.map((d) => [d.data, u.nome, d.real, d.previsto, d.inf, d.sup, d.real >= d.inf && d.real <= d.sup ? "Sim" : "Não", d.naive]),
      ),
    }),
  },
  {
    id: "planilhas",
    grupo: "Base de dados",
    titulo: "Planilhas importadas",
    descricao: `As ${dados.importacao.arquivos.length} planilhas mensais do relatório “Contas a Receber” que formam a base.`,
    uso: "Conferir se algum mês está faltando ou foi carregado em duplicidade.",
    filtros: [],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: () => ({
      colunas: [
        { titulo: "Arquivo", tipo: "texto" },
        { titulo: "Mês", tipo: "texto" },
        { titulo: "Registros", tipo: "numero" },
        { titulo: "Duplicatas", tipo: "numero" },
        { titulo: "Processado em", tipo: "data" },
        { titulo: "Assinatura (hash)", tipo: "texto" },
      ],
      linhas: dados.importacao.arquivos.map((a) => [a.arquivo, a.competencia, a.registros, a.duplicatas, a.processado_em, a.hash]),
    }),
  },
];

// ---------------------------------------------------------------------------
// Relatório gerencial (PDF): resumo de uma página para a gestão
// ---------------------------------------------------------------------------

const CSS_IMPRESSAO = `
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", Roboto, Arial, sans-serif; color: #1a2e1e; margin: 24px; font-size: 11px; }
  h1 { font-size: 18px; margin: 0 0 2px; color: #16472c; }
  h2 { font-size: 13px; margin: 18px 0 6px; color: #16472c; border-bottom: 2px solid #1a6b3c; padding-bottom: 3px; }
  .sub { color: #5a7260; margin: 0 0 12px; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .kpi { border: 1px solid #cfe3c8; border-radius: 6px; padding: 8px; }
  .kpi b { display: block; font-size: 16px; }
  .kpi span { color: #5a7260; }
  table { width: 100%; border-collapse: collapse; margin-top: 4px; }
  th { background: #1a6b3c; color: #fff; text-align: left; padding: 4px 6px; font-weight: 600; }
  td { padding: 3px 6px; border-bottom: 1px solid #e5efe0; }
  .num { text-align: right; }
  tr:nth-child(even) td { background: #f4f9f1; }
  .nota { color: #5a7260; margin-top: 6px; }
  @media print { body { margin: 10mm; } h2 { break-after: avoid; } table { break-inside: auto; } tr { break-inside: avoid; } }
`;

export function documentoImpressao(titulo: string, subtitulo: string, corpo: string): string {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title><style>${CSS_IMPRESSAO}</style></head>
<body><h1>${titulo}</h1><p class="sub">${subtitulo}</p>${corpo}
<p class="nota">Floricultura Verde Perto · Sistema de Previsão de Vendas · gerado em ${new Date().toLocaleString("pt-BR")}</p></body></html>`;
}

export function relatorioGerencialHtml(f: FiltrosRelatorio): string {
  const previsao = previsaoDe(f.unidade);
  const lojas = unidadesDoFiltro(f.unidade);
  const total = somar(previsao.map((d) => d.previsto));
  const inf = somar(previsao.map((d) => d.inf));
  const sup = somar(previsao.map((d) => d.sup));
  const abertos = previsao.filter((d) => !d.loja_fechada).length;
  const ini = previsao[0]!.data;
  const fim = previsao[previsao.length - 1]!.data;

  const kpis = `<div class="kpis">
    <div class="kpi"><span>Venda prevista (${HORIZONTE_DIAS} dias)</span><b>${formatarNumero(total)}</b><span>faixa ${formatarNumero(inf)} a ${formatarNumero(sup)}</span></div>
    <div class="kpi"><span>Média por dia aberto</span><b>${formatarNumero(total / Math.max(1, abertos))}</b><span>${abertos} dias abertos</span></div>
    ${lojas
      .map(
        (u) =>
          `<div class="kpi"><span>Confiança · ${u.nome}</span><b>${estiloStatus[u.modelo.status].label}</b><span>MASE ${formatarDecimal(u.modelo.metricas.mase)} · faixa acertou ${formatarDecimal(u.modelo.metricas.cobertura_ic95_pct, 1)}%</span></div>`,
      )
      .join("")}
  </div>`;

  const porCategoria = tabelaHtml(
    {
      colunas: [
        { titulo: "Categoria", tipo: "texto" },
        { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
        { titulo: "Parte do total", tipo: "texto" },
      ],
      linhas: categorias.map((c) => {
        const v = somar(previsao.map((d) => d.categorias[c.id].previsto));
        return [c.nome, v, formatarPercentual(total ? v / total : 0)];
      }),
    },
    formatarCelula,
  );

  const diaria = tabelaHtml(
    {
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        ...categorias.map((c) => ({ titulo: c.nome, tipo: "numero" as const })),
        { titulo: "Total provável", tipo: "numero" },
        { titulo: "Faixa", tipo: "texto" },
        { titulo: "Obs.", tipo: "texto" },
      ],
      linhas: previsao.map((d) => [
        d.data,
        d.dia_semana,
        ...categorias.map((c) => d.categorias[c.id].previsto),
        d.previsto,
        `${formatarNumero(d.inf)} – ${formatarNumero(d.sup)}`,
        [d.loja_fechada ? "Fechada" : "", d.evento ?? ""].filter(Boolean).join(" · "),
      ]),
    },
    formatarCelula,
  );

  const top = tabelaHtml(
    {
      colunas: [
        { titulo: "Produto", tipo: "texto" },
        { titulo: "Código", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Vendido 8 sem.", tipo: "numero" },
        { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
      ],
      linhas: produtosDe(f.unidade)
        .sort((a, b) => b.previsao_14d - a.previsao_14d)
        .slice(0, 15)
        .map((p) => [p.nome, p.codigo, nomeCategoria(p.categoria), p.vendido_8_semanas, p.previsao_14d]),
    },
    formatarCelula,
  );

  const nota =
    f.unidade === "todas"
      ? `<p class="nota">Todas as lojas: soma das previsões de cada loja. A faixa somada é conservadora (mais larga que a faixa exata da soma).</p>`
      : "";

  return documentoImpressao(
    `Previsão de vendas · ${nomeUnidade(f.unidade)}`,
    `Próximos ${HORIZONTE_DIAS} dias: ${formatarData(ini)} a ${formatarData(fim)} · vendas registradas até ${formatarData(dados.base.fim)}`,
    `${kpis}${nota}<h2>Por categoria</h2>${porCategoria}<h2>Dia a dia</h2>${diaria}<h2>Produtos com maior venda prevista</h2>${top}
     <p class="nota">Venda mais provável = valor do meio (metade dos dias vende mais, metade menos). Faixa provável = intervalo de 95%.
     Flores de corte (~2% do volume) entram na previsão da loja, mas não têm painel próprio.</p>`,
  );
}

export const relatorioGerencial = {
  id: "gerencial",
  titulo: "Relatório gerencial",
  descricao: "Resumo para a gestão: previsão dos próximos 14 dias, por categoria e dia, produtos de maior venda e confiança da previsão.",
  uso: "Levar para a reunião semanal ou enviar para os gerentes das lojas.",
};
