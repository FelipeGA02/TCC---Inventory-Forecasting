export type Urgencia = "critico" | "atencao" | "ok";

export type StatusModelo = "trained" | "low_confidence" | "insufficient_data" | "training";

export type Perfil = "admin" | "viewer";

export interface Usuario {
  id: number;
  email: string;
  perfil: Perfil;
}

export interface Unidade {
  id: string;
  nome: string;
  cidade: string;
}

export interface Produto {
  id: string;
  nome: string;
  grupo: string;
}

export interface PontoTendencia {
  semana: string;
  "Rosa Vermelha": number;
  "Lírio Branco": number;
  Girassol: number;
}

export interface AlertaUrgente {
  id: number;
  produto: string;
  unidade: string;
  estoque: number;
  minimo: number;
  prazo: string;
  urgencia: Urgencia;
}

export interface AlertaReposicao {
  id: number;
  produto: string;
  grupo: string;
  unidade: string;
  estoqueAtual: number;
  estoqueMinimo: number;
  qtdRecomendada: number;
  prazo: string;
  urgencia: Urgencia;
}

export interface PontoPrevisao {
  semana: string;
  quantidade: number;
  inf: number | null;
  sup: number | null;
}

export interface LinhaPrevisaoSemanal {
  semana: string;
  recomendada: number;
  total: number;
}

export interface RegistroImportado {
  id: number;
  data: string;
  produto: string;
  unidade: string;
  quantidade: number;
}

export interface PontoSimulacao {
  dia: string;
  semPromo: number;
}

export interface RelatorioGerado {
  id: number;
  nome: string;
  formato: "PDF" | "Excel";
  data: string;
  tamanho: string;
  usuario: string;
}

export interface IndicadorDashboard {
  chave: "estoque-critico" | "mape" | "produtos-monitorados" | "proximo-calculo";
  valor: string;
  descricao: string;
  tendencia: "alta" | "baixa" | "neutra";
  ajuda?: string;
}

export interface MetricaModelo {
  sigla: string;
  valor: string;
  explicacao: string;
}

export interface EventoSazonal {
  semana: string;
  nome: string;
  impactoEsperado: number;
}
