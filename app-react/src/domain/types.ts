/**
 * Tipos do frontend, no formato que os endpoints `/api/v1/*` devolvem (`ia-predictor/openapi.yaml`).
 *
 * Previsão (ADR-017), treinada pelo botão "Treinar previsões":
 *  - encomendas grandes (nota acima do limiar da loja: média + 4 desvios-padrão da quantidade
 *    dos pedidos dela, ADR-018) ficam fora da previsão e aparecem à parte;
 *  - cada uma das 4 categorias e cada produto de grama, em cada loja, tem o seu SARIMAX
 *    (m = 7, d = 0, D = 0, janela deslizante de 365 dias, testado dia a dia em 8 semanas);
 *  - o total da loja é a soma das 4 categorias.
 */

export type StatusModelo = "trained" | "low_confidence" | "insufficient_data" | "error" | "training";

export type Perfil = "admin" | "viewer";

export interface Usuario {
  id: number;
  email: string;
  nome: string;
  perfil: Perfil;
}

export type CategoriaId = "grama" | "plantas-diversas" | "produtos-de-jardim" | "flores-de-corte";
export type UnidadeId = "jardim-canada" | "itabirito";
/** Filtro de loja nas telas: uma unidade ou as duas somadas. */
export type FiltroUnidade = UnidadeId | "todas";
/** Filtro de categoria nas telas. */
export type FiltroCategoria = CategoriaId | "todas";

export type PorCategoria<T> = Record<CategoriaId, T>;

export interface Categoria {
  id: CategoriaId;
  nome: string;
  grupo: string;
  descricao: string;
}

export interface Faixa {
  previsto: number;
  inf: number;
  sup: number;
}

export interface DiaPrevisto extends Faixa {
  data: string;
  dia_semana: string;
  loja_fechada: boolean;
  evento: string | null;
  categorias: PorCategoria<Faixa>;
}

/**
 * Uma data comemorativa que mudou a previsão de uma série nos 14 dias (ADR-019): a alta de
 * Flores de corte (multiplicador > 1) ou a queda das outras séries no fim de ano e no Dia do
 * Trabalho (multiplicador < 1).
 */
export interface AjusteData {
  nivel: "categoria" | "produto";
  /** Id da categoria ou código do produto de grama. */
  item: string;
  /** Nome do produto (nulo na categoria). */
  nome: string | null;
  evento: string;
  data: string;
  /** O que multiplicou o previsto e a faixa desses dias. */
  multiplicador: number;
  /** Venda ÷ semana comum nas ocorrências passadas. */
  fator: number;
  anos: number[];
  dias: string[];
}

export interface DiaHistorico {
  data: string;
  dia_semana: string;
  /** Venda sem encomendas grandes (soma das 3 categorias). */
  total: number;
  /** Volume vendido em encomendas grandes no dia (fora da previsão). */
  encomendas: number;
  categorias: PorCategoria<number>;
}

export interface SemanaHistorico {
  /** Segunda-feira da semana (AAAA-MM-DD). */
  semana: string;
  total: number;
  encomendas: number;
  categorias: PorCategoria<number>;
}

/** Teste de acerto (walk-forward): cada "rodada" é uma previsão de 14 dias, com a origem andando 1 dia. */
export interface MetricasModelo {
  rodadas: number;
  rodadas_vence_naive: number | null;
  dias_avaliados: number;
  mae: number;
  mase: number;
  erro_relativo_naive: number | null;
  cobertura_ic95_pct: number;
  largura_ic95: number;
  venda_media_dia: number;
  previsto_sobre_real_pct: number | null;
  erro_total_14d_pct: number | null;
  /** Resíduos do ajuste final: p ≤ 0,05 aponta correlação (Ljung-Box) ou fuga da normal (Shapiro-Wilk). */
  ljung_box_p: number | null;
  shapiro_p: number | null;
}

/** SARIMAX de uma categoria ou de um produto de grama numa loja. Sem previsão: só status e motivo. */
export interface ModeloSerie {
  ordem: number[] | null;
  ordem_sazonal: number[] | null;
  aic: number | null;
  status: StatusModelo;
  metricas: MetricasModelo | null;
  /** Por que a série ficou sem previsão (poucos dados, falha no ajuste). */
  mensagem: string | null;
}

/** Produto de grama de uma loja, com o seu modelo (sem previsão se vendeu pouco). */
export interface Produto {
  codigo: string;
  nome: string;
  categoria: CategoriaId;
  subcategoria: string;
  dias_com_venda: number;
  pct_dias_abertos_com_venda: number;
  media_dia_aberto: number;
  vendido_8_semanas: number;
  vendido_total: number;
  vendido_em_encomendas: number;
  /** Venda das últimas 8 semanas, da mais antiga para a mais recente. */
  historico_semanal: number[];
  /** Venda diária (sem encomendas grandes) dos últimos 28 dias. */
  historico_diario?: { data: string; vendido: number }[];
  modelo: ModeloSerie;
  /** Vazia quando o produto ficou sem modelo neste treino. `fator`: multiplicador da data comemorativa. */
  previsao: (Faixa & { data: string; fator?: number | null })[];
  previsao_14d: number | null;
}

/** Produto com a loja a que pertence (para o filtro "Todas as lojas"). */
export type ProdutoDaLoja = Produto & { unidade: UnidadeId; nomeUnidade: string };

export interface Encomendas {
  vendas: number;
  dias: number;
  volume: number;
  pct_volume: number;
  ultimas: { data: string; volume: number; produtos: string[] }[];
}

export interface DiaBacktest extends Faixa {
  data: string;
  real: number;
  naive: number;
}

/**
 * Um dia do histórico da previsão (`/api/v1/painel/historico/...`): o vendido sem encomendas
 * grandes e o previsto congelado — o da última previsão feita antes do dia. Nulo antes do 1º treino.
 */
export interface DiaHistoricoPrevisao {
  data: string;
  real: number;
  previsto: number | null;
  inf: number | null;
  sup: number | null;
  /** "forecast": a previsão que a loja viu; "walk_forward": dia que nenhuma previsão cobriu. */
  fonte: "forecast" | "walk_forward" | null;
  /** A quantos dias do início da previsão o dia estava (1 no walk-forward). */
  horizonte: number | null;
  /** Se a previsão contava com a loja fechada no dia (calendário da época). */
  loja_fechada: boolean | null;
  /** A data comemorativa que mudou o previsto do dia; o do modelo sem ela é previsto ÷ multiplicador. */
  ajuste?: { evento: string | null; multiplicador: number } | null;
}

export interface UnidadeDados {
  id: UnidadeId;
  nome: string;
  cidade: string;
  periodo: { inicio: string; fim: string; dias: number };
  linhas: number;
  skus_vendidos: number;
  volume_total: number;
  volume_flores_de_corte: number;
  volume_por_categoria: PorCategoria<number>;
  skus_por_categoria: PorCategoria<number>;
  encomendas: Encomendas;
  /** O SARIMAX de cada categoria nesta loja (nulo se a categoria não entrou no treino). */
  categorias_modelo: PorCategoria<ModeloSerie | null>;
  /** 14 dias a partir do dia seguinte à última venda; o total é a soma das 4 categorias. */
  previsao: DiaPrevisto[];
  /** As datas comemorativas que mudaram a previsão das séries da loja (ADR-019). */
  ajustes_datas?: AjusteData[];
  historico_diario: DiaHistorico[];
  historico_semanal: SemanaHistorico[];
  produtos: Produto[];
  /** Teste de acerto de cada categoria, dia a dia: o 1º dia de cada janela do walk-forward. */
  backtest_categorias: PorCategoria<DiaBacktest[]>;
}

export interface ArquivoImportado {
  arquivo: string;
  competencia: string;
  /** Primeiro e último dia de venda da planilha (nulos nas da carga inicial). */
  inicio: string | null;
  fim: string | null;
  registros: number;
  duplicatas: number;
  hash: string;
  processado_em: string;
}

export interface BaseReal {
  gerado_em: string;
  fonte: string;
  base: {
    inicio: string;
    fim: string;
    linhas: number;
    skus: number;
    skus_por_categoria: PorCategoria<number>;
  };
  /** O treino que gerou a previsão (`forecast_jobs.config`). */
  configuracao: {
    horizonte_dias: number;
    m: number;
    d: number;
    D: number;
    alpha_ic: number;
    janela_dias: number;
    origens: number;
    passo_origem_dias: number;
    limiares_encomenda_un: Record<UnidadeId, number>;
    base: string;
    categoria_produtos: string;
    versao_codigo: string | null;
    dados_ate: string;
  };
  categorias: Categoria[];
  unidades: UnidadeDados[];
  importacao: {
    arquivos: ArquivoImportado[];
    qualidade: {
      linhas_lidas: number;
      linhas_removidas: number;
      clientes_sem_nome_corrigidos: number;
      duplicatas: number;
    };
  };
}

/**
 * O pouco que o layout precisa logo depois do login (`GET /api/v1/contexto`): lojas,
 * categorias, período da base, status dos previsores e planilhas carregadas. As telas pedem
 * o resto (painel, análises, registros) quando são abertas.
 */
export interface Contexto {
  lojas: { id: UnidadeId; nome: string; cidade: string }[];
  categorias: Categoria[];
  /** treino_na_api: falso quando a API não treina (Render) — o front não oferece "Treinar previsões" */
  configuracao: { horizonte_dias: number; limiares_encomenda_un: Record<UnidadeId, number>; treino_na_api: boolean };
  base: { inicio: string | null; fim: string | null; linhas: number; skus: number };
  /** O último treino concluído; nulo antes do primeiro. */
  previsao: {
    gerada_em: string;
    dados_ate: string;
    categorias: { loja: UnidadeId; categoria: CategoriaId; status: StatusModelo }[];
    produtos: { loja: UnidadeId; codigo: string; nome: string; status: StatusModelo }[];
  } | null;
  importacao: BaseReal["importacao"];
}
