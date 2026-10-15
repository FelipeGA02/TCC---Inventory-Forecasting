/**
 * Tipos do frontend. Reproduzem o JSON gerado por
 * `ia-predictor/training_scripts/frontend_mock/gerar_dados_frontend.py`, que por sua vez
 * segue o formato que os endpoints `/api/v1/*` devolverão.
 *
 * Metodologia (etapa de testes, e-mail ao orientador):
 *  - encomendas (venda > 2.000 un. na nota) ficam fora da previsão e aparecem à parte;
 *  - loja: SARIMAX na venda sem encomendas, sem log1p, janela deslizante;
 *  - categoria: participação na previsão da loja (filtro de leitura, sem modelo próprio);
 *  - produto regular: SARIMAX no próprio produto; demais produtos só com histórico.
 */

export type StatusModelo = "trained" | "low_confidence" | "insufficient_data" | "training";

export type Perfil = "admin" | "viewer";

export interface Usuario {
  id: number;
  email: string;
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

export interface DiaHistorico {
  data: string;
  dia_semana: string;
  /** Venda sem encomendas (soma das 3 categorias). */
  total: number;
  /** Volume vendido em encomendas no dia (fora da previsão). */
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

export interface MetricasModelo {
  rodadas: number;
  rodadas_vence_naive: number;
  dias_avaliados: number;
  mae: number;
  mase: number;
  erro_relativo_naive: number | null;
  cobertura_ic95_pct: number;
  largura_ic95: number;
  venda_media_dia: number;
  previsto_sobre_real_pct: number | null;
  erro_total_14d_pct: number | null;
}

export interface RodadaValidacao {
  origem: string;
  erro_modelo: number;
  erro_naive: number;
}

export interface ModeloUnidade {
  ordem: number[];
  ordem_sazonal: number[];
  aic: number;
  transformacao: string;
  janela: string;
  janela_dias: number;
  base: string;
  exogenas: string[];
  status: StatusModelo;
  metricas: MetricasModelo;
  rodadas: RodadaValidacao[];
}

export interface ModeloProduto {
  ordem: number[];
  ordem_sazonal: number[];
  metricas: MetricasModelo | null;
  status: StatusModelo;
}

export interface Produto {
  codigo: string;
  nome: string;
  categoria: CategoriaId;
  subcategoria: string;
  /** Venda regular (ADI < 1,32) → tem modelo e previsão diária próprios. */
  regular: boolean;
  dias_com_venda: number;
  pct_dias_abertos_com_venda: number;
  media_dia_aberto: number;
  vendido_8_semanas: number;
  vendido_total: number;
  vendido_em_encomendas: number;
  /** Venda das últimas 8 semanas, da mais antiga para a mais recente. */
  historico_semanal: number[];
  /** Venda diária (sem encomendas) dos últimos 28 dias. */
  historico_diario?: { data: string; vendido: number }[];
  modelo: ModeloProduto | null;
  previsao: (Faixa & { data: string })[];
  previsao_14d: number | null;
  /** Previsto × vendido em todo o período testado (rodadas de 14 dias). */
  backtest?: DiaBacktest[];
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

export interface DesagregacaoCategoria {
  metricas: MetricasModelo;
  status: StatusModelo;
  backtest: DiaBacktest[];
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
  regulares_por_categoria: PorCategoria<number>;
  /** % da venda (sem encomendas) das últimas 8 semanas que vem dos produtos regulares. */
  volume_regulares_8_semanas_pct: PorCategoria<number>;
  flores_regulares_fora_do_painel: number;
  encomendas: Encomendas;
  modelo: ModeloUnidade;
  previsao: DiaPrevisto[];
  historico_diario: DiaHistorico[];
  historico_semanal: SemanaHistorico[];
  produtos: Produto[];
  backtest: DiaBacktest[];
  /** Desagregação loja → categoria, testada nas mesmas rodadas da loja. */
  desagregacao: PorCategoria<DesagregacaoCategoria>;
}

export interface RegistroVenda {
  data: string;
  documento: string;
  codigo: string;
  produto: string;
  unidade: UnidadeId;
  categoria: CategoriaId | "flores-de-corte";
  quantidade: number;
  valor: number;
  tipo_cliente: "Consumidor" | "Cadastrado";
  encomenda: boolean;
}

export interface ArquivoImportado {
  arquivo: string;
  competencia: string;
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
  configuracao: {
    horizonte_dias: number;
    m: number;
    alpha_ic: number;
    janela_participacao_dias: number;
    primeira_origem_validacao: string;
    passo_origem_dias: number;
    limiar_encomenda_un: number;
    criterio_regular: { adi_corte: number; min_span_dias: number; fonte: string };
    modelo_loja: string;
    modelo_produto: string;
  };
  categorias: Categoria[];
  unidades: UnidadeDados[];
  registros_amostra: RegistroVenda[];
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
