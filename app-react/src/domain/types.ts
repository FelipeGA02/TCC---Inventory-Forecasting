/**
 * Tipos do frontend. Reproduzem o JSON gerado por
 * `ia-predictor/training_scripts/frontend_mock/gerar_dados_frontend.py`, que por sua vez
 * segue o formato que os endpoints `/api/v1/*` devolverão.
 */

export type StatusModelo = "trained" | "low_confidence" | "insufficient_data" | "training";

export type Perfil = "admin" | "viewer";

export interface Usuario {
  id: number;
  email: string;
  perfil: Perfil;
}

export type CategoriaId = "grama" | "plantas-diversas" | "produtos-de-jardim";
export type UnidadeId = "jardim-canada" | "itabirito";
/** Filtro de loja nas telas: uma unidade ou as duas somadas. */
export type FiltroUnidade = UnidadeId | "todas";

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
  total: number;
  categorias: PorCategoria<number>;
}

export interface SemanaHistorico {
  /** Segunda-feira da semana (AAAA-MM-DD). */
  semana: string;
  total: number;
  categorias: PorCategoria<number>;
}

export interface ProdutoPrevisto {
  codigo: string;
  nome: string;
  categoria: CategoriaId;
  subcategoria: string;
  vendido_8_semanas: number;
  vendido_total: number;
  dias_com_venda: number;
  vendas: number;
  participacao_categoria: number;
  /** Venda das últimas 8 semanas, da mais antiga para a mais recente. */
  historico_semanal: number[];
  previsao_14d: number;
  previsao: (Faixa & { data: string })[];
}

export interface MetricasModelo {
  rodadas: number;
  rodadas_vence_naive: number;
  dias_avaliados: number;
  mae: number;
  mase: number;
  erro_relativo_naive: number;
  cobertura_ic95_pct: number;
  largura_ic95: number;
  previsto_sobre_real_pct: number;
  mape_dias_abertos_pct: number;
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
  exogenas: string[];
  status: StatusModelo;
  metricas: MetricasModelo;
  rodadas: RodadaValidacao[];
}

export interface DiaBacktest extends Faixa {
  data: string;
  real: number;
  naive: number;
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
  /** Participação de cada categoria por dia da semana (seg…dom) nas últimas 8 semanas. */
  participacao_dia_semana: PorCategoria<number[]>;
  modelo: ModeloUnidade;
  previsao: DiaPrevisto[];
  historico_diario: DiaHistorico[];
  historico_semanal: SemanaHistorico[];
  produtos: ProdutoPrevisto[];
  backtest: DiaBacktest[];
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
