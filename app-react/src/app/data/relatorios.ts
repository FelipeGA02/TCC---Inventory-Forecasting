/**
 * Catálogo de relatórios para download. Cada relatório monta uma tabela a partir dos dados
 * reais (`mockData`) e dos filtros escolhidos; a tela decide o formato (XLSX, CSV ou PDF).
 */
import type { CategoriaId, FiltroCategoria, FiltroUnidade, ModeloSerie } from "@/domain/types";
import { estiloStatus } from "@/styles/tokens";
import { formatarData, formatarDecimal, formatarDiaMes, formatarNumero, formatarPercentual, formatarQtd } from "@/lib/format";
import { tabelaHtml, type Celula, type Tabela, type TipoColuna } from "@/lib/exportar";
import {
  HORIZONTE_DIAS,
  IDS_CATEGORIA,
  LIMIAR_ENCOMENDA,
  categorias,
  dados,
  encomendasDe,
  faixaDoDia,
  nomeCategoria,
  nomeUnidade,
  previsaoDe,
  produtosDe,
  somar,
  unidadesDoFiltro,
} from "./mockData";

export type Formato = "xlsx" | "csv" | "pdf";
export type { FiltroCategoria };

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
}

const cats = (f: FiltrosRelatorio): CategoriaId[] => (f.categoria === "todas" ? IDS_CATEGORIA : [f.categoria]);
const r1 = (v: number) => Math.round(v * 10) / 10;
const ordemModelo = (m: ModeloSerie) =>
  m.ordem && m.ordem_sazonal ? `SARIMAX(${m.ordem.join(",")})(${m.ordem_sazonal.join(",")})` : "";
const situacao = (m: ModeloSerie | null) => (m ? estiloStatus[m.status].label : "Sem previsão");

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
    descricao: "Previsão e faixa provável (95%) por dia, loja e categoria — cada categoria com o seu modelo. Venda do dia a dia, sem as encomendas grandes.",
    uso: "Planejar o recebimento de mercadoria e a equipe de cada dia.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Previsão", tipo: "numero" },
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
    titulo: "Previsão por produto de grama",
    descricao: `Produtos de grama, cada um com o seu modelo em cada loja: total previsto e previsão de cada um dos ${HORIZONTE_DIAS} dias.`,
    uso: "Conferir o volume esperado de cada grama antes de fazer o pedido.",
    filtros: ["unidade"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => {
      const dias = previsaoDe(f.unidade).map((d) => d.data);
      return {
        colunas: [
          { titulo: "Loja", tipo: "texto" },
          { titulo: "Código", tipo: "texto" },
          { titulo: "Produto", tipo: "texto" },
          { titulo: "Confiança", tipo: "texto" },
          { titulo: "Vendido 8 semanas", tipo: "numero" },
          { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
          ...dias.map((d) => ({ titulo: formatarDiaMes(d), tipo: "numero" as const })),
        ],
        linhas: produtosDe(f.unidade, "grama", true).map((p) => [
          p.nomeUnidade,
          p.codigo,
          p.nome,
          situacao(p.modelo),
          p.vendido_8_semanas,
          p.previsao_14d,
          ...p.previsao.map((d) => d.previsto),
        ]),
      };
    },
  },
  {
    id: "vendas-semanais",
    grupo: "Histórico de vendas",
    titulo: "Vendas por semana · base completa",
    descricao: `Quantidade vendida por semana e categoria, de ${formatarData(dados.base.inicio)} a ${formatarData(dados.base.fim)}, com as encomendas grandes em coluna à parte.`,
    uso: "Comparar com o mesmo período do ano anterior e ver a sazonalidade.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Semana (segunda)", tipo: "data" },
        { titulo: "Loja", tipo: "texto" },
        ...cats(f).map((c) => ({ titulo: nomeCategoria(c), tipo: "numero" as const })),
        { titulo: "Total sem encomendas grandes", tipo: "numero" },
        { titulo: "Encomendas grandes", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.historico_semanal.map((s) => [
          s.semana,
          u.nome,
          ...cats(f).map((c) => s.categorias[c]),
          r1(somar(cats(f).map((c) => s.categorias[c]))),
          s.encomendas,
        ]),
      ),
    }),
  },
  {
    id: "vendas-diarias",
    grupo: "Histórico de vendas",
    titulo: "Vendas por dia · últimas 8 semanas",
    descricao: "O movimento recente de cada categoria, dia a dia.",
    uso: "Conferir o movimento recente dia a dia.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        ...cats(f).map((c) => ({ titulo: nomeCategoria(c), tipo: "numero" as const })),
        { titulo: "Total sem encomendas grandes", tipo: "numero" },
        { titulo: "Encomendas grandes", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.historico_diario.map((d) => [
          d.data,
          d.dia_semana,
          u.nome,
          ...cats(f).map((c) => d.categorias[c]),
          r1(somar(cats(f).map((c) => d.categorias[c]))),
          d.encomendas,
        ]),
      ),
    }),
  },
  {
    id: "encomendas",
    grupo: "Histórico de vendas",
    titulo: "Encomendas grandes por semana",
    descricao: `Volume vendido em notas com mais de ${formatarNumero(LIMIAR_ENCOMENDA)} unidades, que fica fora da previsão.`,
    uso: "Acompanhar quando as vendas grandes acontecem e quanto pesam.",
    filtros: ["unidade"],
    formatos: ["xlsx", "csv"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Semana (segunda)", tipo: "data" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Encomendas grandes", tipo: "numero" },
        { titulo: "Venda sem encomendas grandes", tipo: "numero" },
        { titulo: "Encomendas grandes no total (%)", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        u.historico_semanal
          .filter((s) => s.encomendas > 0)
          .map((s) => [s.semana, u.nome, s.encomendas, s.total, r1((s.encomendas / (s.total + s.encomendas)) * 100)]),
      ),
    }),
  },
  {
    id: "acerto-resumo",
    grupo: "Qualidade da previsão",
    titulo: "Acerto da previsão de cada categoria",
    descricao: "Indicadores do teste de acerto do último treino, por loja e categoria (venda sem encomendas grandes).",
    uso: "Saber quanto confiar na previsão de cada categoria em cada loja.",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Situação", tipo: "texto" },
        { titulo: "MASE", tipo: "decimal" },
        { titulo: "Erro ÷ naive sazonal", tipo: "decimal" },
        { titulo: "Cobertura do intervalo de 95% (%)", tipo: "numero" },
        { titulo: "Previsões de 14 dias que vencem a naive", tipo: "texto" },
        { titulo: "Erro no total de 14 dias (%)", tipo: "numero" },
        { titulo: "Volume previsto ÷ vendido (%)", tipo: "numero" },
        { titulo: "Modelo", tipo: "texto" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        cats(f).map((c) => {
          const mod = u.categorias_modelo[c];
          const m = mod?.metricas;
          return [
            u.nome,
            nomeCategoria(c),
            situacao(mod),
            m?.mase ?? null,
            m?.erro_relativo_naive ?? null,
            m?.cobertura_ic95_pct ?? null,
            m ? `${m.rodadas_vence_naive ?? "—"} de ${m.rodadas}` : "",
            m?.erro_total_14d_pct ?? null,
            m?.previsto_sobre_real_pct ?? null,
            mod ? `${ordemModelo(mod)} · sem encomendas grandes · janela deslizante de ${dados.configuracao.janela_dias} dias` : "",
          ];
        }),
      ),
    }),
  },
  {
    id: "acerto-produtos",
    grupo: "Qualidade da previsão",
    titulo: "Acerto de cada produto de grama",
    descricao: "Como a previsão de cada produto de grama se saiu no teste de acerto do último treino.",
    uso: "Saber em quais gramas a previsão diária é confiável.",
    filtros: ["unidade"],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Código", tipo: "texto" },
        { titulo: "Produto", tipo: "texto" },
        { titulo: "Situação", tipo: "texto" },
        { titulo: "MASE", tipo: "decimal" },
        { titulo: "Cobertura do intervalo de 95% (%)", tipo: "numero" },
        { titulo: "Volume previsto ÷ vendido (%)", tipo: "numero" },
        { titulo: "Erro no total de 14 dias (%)", tipo: "numero" },
        { titulo: "Previsões de 14 dias que vencem a naive", tipo: "texto" },
      ],
      linhas: produtosDe(f.unidade, "grama", true)
        .filter((p) => p.modelo.metricas)
        .map((p) => {
          const m = p.modelo.metricas!;
          return [
            p.nomeUnidade,
            p.codigo,
            p.nome,
            situacao(p.modelo),
            m.mase,
            m.cobertura_ic95_pct,
            m.previsto_sobre_real_pct,
            m.erro_total_14d_pct,
            `${m.rodadas_vence_naive ?? "—"} de ${m.rodadas}`,
          ];
        }),
    }),
  },
  {
    id: "acerto-dias",
    grupo: "Qualidade da previsão",
    titulo: "Teste de acerto por categoria · dia a dia",
    descricao: "Cada dia testado no último treino: o que o modelo previu com as vendas até a véspera, a faixa, o que foi vendido (sem encomendas grandes) e o naive sazonal.",
    uso: "Auditar a previsão em datas específicas (feriados, picos de venda).",
    filtros: ["unidade", "categoria"],
    formatos: ["xlsx", "csv"],
    gerar: (f) => ({
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Vendido", tipo: "numero" },
        { titulo: "Previsto", tipo: "numero" },
        { titulo: "Mínimo provável", tipo: "numero" },
        { titulo: "Máximo provável", tipo: "numero" },
        { titulo: "Dentro da faixa", tipo: "texto" },
        { titulo: "Naive sazonal", tipo: "numero" },
      ],
      linhas: unidadesDoFiltro(f.unidade).flatMap((u) =>
        cats(f).flatMap((c) =>
          u.backtest_categorias[c].map((d) => [
            d.data,
            u.nome,
            nomeCategoria(c),
            d.real,
            d.previsto,
            d.inf,
            d.sup,
            d.real >= d.inf && d.real <= d.sup ? "Sim" : "Não",
            d.naive,
          ]),
        ),
      ),
    }),
  },
  {
    id: "planilhas",
    grupo: "Base de dados",
    titulo: "Planilhas importadas",
    descricao: `As ${dados.importacao.arquivos.length} planilhas do relatório “Contas a Receber” que formam a base.`,
    uso: "Conferir se algum período está faltando ou foi carregado em duplicidade.",
    filtros: [],
    formatos: ["xlsx", "csv", "pdf"],
    gerar: () => ({
      colunas: [
        { titulo: "Arquivo", tipo: "texto" },
        { titulo: "Mês", tipo: "texto" },
        { titulo: "Primeiro dia", tipo: "data" },
        { titulo: "Último dia", tipo: "data" },
        { titulo: "Registros", tipo: "numero" },
        { titulo: "Duplicatas", tipo: "numero" },
        { titulo: "Processado em", tipo: "data" },
        { titulo: "Assinatura (hash)", tipo: "texto" },
      ],
      linhas: dados.importacao.arquivos.map((a) => [a.arquivo, a.competencia, a.inicio, a.fim, a.registros, a.duplicatas, a.processado_em, a.hash]),
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
  @media print { body { margin: 10mm; } h2 { break-after: avoid; } tr { break-inside: avoid; } }
`;

export function documentoImpressao(titulo: string, subtitulo: string, corpo: string): string {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title><style>${CSS_IMPRESSAO}</style></head>
<body><h1>${titulo}</h1><p class="sub">${subtitulo}</p>${corpo}
<p class="nota">Floricultura Verde Perto · Sistema de Previsão de Vendas · gerado em ${new Date().toLocaleString("pt-BR")}</p></body></html>`;
}

export function relatorioGerencialHtml(f: FiltrosRelatorio): string {
  const previsao = previsaoDe(f.unidade);
  const lojas = unidadesDoFiltro(f.unidade);
  const faixas = previsao.map((d) => faixaDoDia(d, f.categoria));
  const total = somar(faixas.map((d) => d.previsto));
  const abertos = previsao.filter((d) => !d.loja_fechada).length;
  const enc = encomendasDe(f.unidade);
  const ini = previsao[0]!.data;
  const fim = previsao[previsao.length - 1]!.data;
  const gramas = produtosDe(f.unidade, "grama", true);

  const kpis = `<div class="kpis">
    <div class="kpi"><span>Previsão (${HORIZONTE_DIAS} dias)</span><b>${formatarNumero(total)}</b><span>faixa ${formatarNumero(somar(faixas.map((d) => d.inf)))} a ${formatarNumero(somar(faixas.map((d) => d.sup)))}</span></div>
    <div class="kpi"><span>Média por dia aberto</span><b>${formatarNumero(total / Math.max(1, abertos))}</b><span>${abertos} dias abertos</span></div>
    <div class="kpi"><span>Produtos de grama com previsão</span><b>${gramas.length}</b><span>cada um com o seu modelo</span></div>
    <div class="kpi"><span>Encomendas grandes (fora da previsão)</span><b>${formatarNumero(enc.vendas)}</b><span>${formatarPercentual(enc.pctVolume / 100)} do volume histórico</span></div>
  </div>`;

  const confianca = tabelaHtml(
    {
      colunas: [
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Situação", tipo: "texto" },
        { titulo: "MASE", tipo: "decimal" },
        { titulo: "Intervalo acertou (%)", tipo: "numero" },
      ],
      linhas: lojas.flatMap((u) =>
        cats(f).map((c) => {
          const mod = u.categorias_modelo[c];
          return [u.nome, nomeCategoria(c), situacao(mod), mod?.metricas?.mase ?? null, mod?.metricas?.cobertura_ic95_pct ?? null];
        }),
      ),
    },
    formatarCelula,
  );

  const porCategoria = tabelaHtml(
    {
      colunas: [
        { titulo: "Categoria", tipo: "texto" },
        { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
        { titulo: "Parte do total", tipo: "texto" },
      ],
      linhas: categorias.map((c) => {
        const v = somar(previsao.map((d) => d.categorias[c.id].previsto));
        const t = somar(previsao.map((d) => d.previsto));
        return [c.nome, v, formatarPercentual(t ? v / t : 0)];
      }),
    },
    formatarCelula,
  );

  const diaria = tabelaHtml(
    {
      colunas: [
        { titulo: "Data", tipo: "data" },
        { titulo: "Dia", tipo: "texto" },
        { titulo: "Previsão", tipo: "numero" },
        { titulo: "Faixa", tipo: "texto" },
        { titulo: "Obs.", tipo: "texto" },
      ],
      linhas: previsao.map((d) => {
        const fx = faixaDoDia(d, f.categoria);
        return [d.data, d.dia_semana, fx.previsto, `${formatarNumero(fx.inf)} – ${formatarNumero(fx.sup)}`, [d.loja_fechada ? "Fechada" : "", d.evento ?? ""].filter(Boolean).join(" · ")];
      }),
    },
    formatarCelula,
  );

  const top = tabelaHtml(
    {
      colunas: [
        { titulo: "Produto", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Confiança", tipo: "texto" },
        { titulo: `Previsto ${HORIZONTE_DIAS} dias`, tipo: "numero" },
      ],
      linhas: gramas.slice(0, 15).map((p) => [p.nome, p.nomeUnidade, situacao(p.modelo), p.previsao_14d]),
    },
    formatarCelula,
  );

  return documentoImpressao(
    `Previsão de vendas · ${nomeUnidade(f.unidade)} · ${nomeCategoria(f.categoria)}`,
    `Próximos ${HORIZONTE_DIAS} dias: ${formatarData(ini)} a ${formatarData(fim)} · vendas registradas até ${formatarData(dados.base.fim)}`,
    `${kpis}<h2>Confiança da previsão</h2>${confianca}${f.categoria === "todas" ? `<h2>Por categoria</h2>${porCategoria}` : ""}<h2>Dia a dia</h2>${diaria}<h2>Produtos de grama</h2>${top}
     <p class="nota">A previsão é da venda do dia a dia; as encomendas grandes (notas com mais de ${formatarNumero(LIMIAR_ENCOMENDA)} unidades) ficam fora.
     Cada categoria e cada produto de grama tem a sua previsão, feita só com a própria venda em cada loja; o total da loja é a soma das 4 categorias.
     Faixa provável = intervalo de 95%.</p>`,
  );
}

export const relatorioGerencial = {
  id: "gerencial",
  titulo: "Relatório gerencial",
  descricao: "Resumo para a gestão: previsão dos próximos 14 dias, por categoria e dia, por produto de grama, encomendas grandes e confiança da previsão.",
  uso: "Levar para a reunião semanal ou enviar para os gerentes das lojas.",
};
