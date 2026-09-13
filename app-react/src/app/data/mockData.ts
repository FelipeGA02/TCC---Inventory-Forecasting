/**
 * Dados fictícios para desenvolvimento do frontend.
 *
 * Enquanto a API (ia-predictor/openapi.yaml) não está conectada, todas as telas
 * consomem este módulo. Os formatos aqui reproduzem o que os endpoints
 * `/api/v1/*` devolverão, para que a troca por chamadas reais seja direta.
 *
 * Cenário: rede de floricultura com 3 unidades · junho/2026.
 */

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

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

export interface PontoPrevisao {
  semana: string;
  quantidade: number;
  /** Limite inferior do intervalo de confiança — `null` no histórico. */
  inf: number | null;
  /** Limite superior do intervalo de confiança — `null` no histórico. */
  sup: number | null;
}

export interface LinhaPrevisaoSemanal {
  semana: string;
  recomendada: number;
  /** Acumulado da coluna `recomendada` até esta semana. */
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

// ---------------------------------------------------------------------------
// Catálogos
// ---------------------------------------------------------------------------

export const unidades: Unidade[] = [
  { id: "centro", nome: "Centro", cidade: "Nova Lima" },
  { id: "jardim-canada", nome: "Jardim Canadá", cidade: "Nova Lima" },
  { id: "itabirito", nome: "Itabirito", cidade: "Itabirito" },
];

export const produtos: Produto[] = [
  { id: "rosa-vermelha", nome: "Rosa Vermelha", grupo: "Rosas" },
  { id: "rosa-branca", nome: "Rosa Branca", grupo: "Rosas" },
  { id: "lirio", nome: "Lírio Branco", grupo: "Lírios" },
  { id: "girassol", nome: "Girassol", grupo: "Tropicais" },
  { id: "orquidea", nome: "Orquídea Phalaenopsis", grupo: "Orquídeas" },
  { id: "crisantemo", nome: "Crisântemo Amarelo", grupo: "Crisântemos" },
  { id: "buque-misto", nome: "Buquê Misto", grupo: "Rosas" },
];

// ---------------------------------------------------------------------------
// Dashboard — tendência das 8 últimas semanas
// O pico de 04/mai reflete o Dia das Mães (10/05/2026).
// ---------------------------------------------------------------------------

export const tendenciaProdutos: PontoTendencia[] = [
  { semana: "27/abr", "Rosa Vermelha": 412, "Lírio Branco": 268, Girassol: 195 },
  { semana: "04/mai", "Rosa Vermelha": 638, "Lírio Branco": 391, Girassol: 242 },
  { semana: "11/mai", "Rosa Vermelha": 474, "Lírio Branco": 302, Girassol: 218 },
  { semana: "18/mai", "Rosa Vermelha": 398, "Lírio Branco": 255, Girassol: 187 },
  { semana: "25/mai", "Rosa Vermelha": 421, "Lírio Branco": 249, Girassol: 203 },
  { semana: "01/jun", "Rosa Vermelha": 456, "Lírio Branco": 271, Girassol: 226 },
  { semana: "08/jun", "Rosa Vermelha": 503, "Lírio Branco": 288, Girassol: 241 },
  { semana: "15/jun", "Rosa Vermelha": 468, "Lírio Branco": 264, Girassol: 233 },
];

// ---------------------------------------------------------------------------
// Previsão SARIMAX — 8 semanas de histórico + horizonte de 4 semanas.
// O histórico usa inf/sup = null (a banda de confiança só existe no futuro).
// Valores dentro do domínio [200, 650] fixado no eixo Y da tela.
// ---------------------------------------------------------------------------

export const previsaoSarimax: PontoPrevisao[] = [
  { semana: "Sem -7", quantidade: 412, inf: null, sup: null },
  { semana: "Sem -6", quantidade: 638, inf: null, sup: null },
  { semana: "Sem -5", quantidade: 474, inf: null, sup: null },
  { semana: "Sem -4", quantidade: 398, inf: null, sup: null },
  { semana: "Sem -3", quantidade: 421, inf: null, sup: null },
  { semana: "Sem -2", quantidade: 456, inf: null, sup: null },
  { semana: "Sem -1", quantidade: 503, inf: null, sup: null },
  { semana: "Atual", quantidade: 468, inf: 468, sup: 468 },
  { semana: "Sem +1", quantidade: 592, inf: 528, sup: 648 },
  { semana: "Sem +2", quantidade: 511, inf: 432, sup: 590 },
  { semana: "Sem +3", quantidade: 487, inf: 392, sup: 582 },
  { semana: "Sem +4", quantidade: 465, inf: 352, sup: 578 },
];

/** Compra recomendada por semana; `total` é o acumulado das 4 semanas. */
export const tabelaPrevisaoSemanal: LinhaPrevisaoSemanal[] = [
  { semana: "Sem +1", recomendada: 620, total: 620 },
  { semana: "Sem +2", recomendada: 535, total: 1155 },
  { semana: "Sem +3", recomendada: 510, total: 1665 },
  { semana: "Sem +4", recomendada: 490, total: 2155 },
];

// ---------------------------------------------------------------------------
// Simulador de Cenários — linha de base de 7 dias (sem promoção).
// A tela calcula "com promoção" a partir destes valores.
// ---------------------------------------------------------------------------

export const dadosSimulacaoBase: PontoSimulacao[] = [
  { dia: "Seg", semPromo: 42 },
  { dia: "Ter", semPromo: 38 },
  { dia: "Qua", semPromo: 51 },
  { dia: "Qui", semPromo: 64 },
  { dia: "Sex", semPromo: 96 },
  { dia: "Sáb", semPromo: 128 },
  { dia: "Dom", semPromo: 73 },
];

// ---------------------------------------------------------------------------
// Exportar Relatórios — histórico de gerações recentes
// ---------------------------------------------------------------------------

export const historicoRelatorios: RelatorioGerado[] = [
  { id: 1, nome: "Relatório completo — Junho", formato: "PDF", data: "22/06/2026 14:32", tamanho: "1,8 MB", usuario: "Gestora" },
  { id: 2, nome: "Quanto comprar — Centro", formato: "Excel", data: "22/06/2026 09:05", tamanho: "412 KB", usuario: "Gerente" },
  { id: 3, nome: "Quanto comprar — Semana 25", formato: "PDF", data: "21/06/2026 17:48", tamanho: "886 KB", usuario: "Gestora" },
  { id: 4, nome: "Qualidade das previsões", formato: "Excel", data: "19/06/2026 11:20", tamanho: "654 KB", usuario: "Gestora" },
  { id: 5, nome: "Simulações de promoções", formato: "PDF", data: "17/06/2026 16:09", tamanho: "1,1 MB", usuario: "Gerente" },
  { id: 6, nome: "Quanto comprar — Itabirito", formato: "Excel", data: "15/06/2026 08:54", tamanho: "388 KB", usuario: "Gerente" },
  { id: 7, nome: "Relatório completo — Maio", formato: "PDF", data: "01/06/2026 10:02", tamanho: "1,7 MB", usuario: "Gestora" },
];

// ---------------------------------------------------------------------------
// Pré-visualização da planilha importada
//
// 63 registros (3 datas × 7 produtos × 3 unidades) gerados de forma
// determinística — sem Math.random, para que a tabela e a paginação sejam
// idênticas a cada recarga da página.
// ---------------------------------------------------------------------------

/** Volume semanal típico por produto na unidade Centro. */
const VOLUME_BASE: Record<string, number> = {
  "rosa-vermelha": 155,
  "rosa-branca": 92,
  lirio: 88,
  girassol: 76,
  orquidea: 34,
  crisantemo: 61,
  "buque-misto": 47,
};

/** Peso de cada unidade sobre o volume base. */
const PESO_UNIDADE: Record<string, number> = {
  centro: 1,
  "jardim-canada": 0.72,
  itabirito: 0.55,
};

/** Variação determinística em [-0,18; +0,18] a partir de uma semente inteira. */
function variacao(semente: number): number {
  const x = Math.sin(semente * 12.9898) * 43758.5453;
  return (x - Math.floor(x) - 0.5) * 0.36;
}

function gerarRegistros(): RegistroImportado[] {
  const datas = ["01/06/2026", "08/06/2026", "15/06/2026"];
  const registros: RegistroImportado[] = [];
  let id = 1;

  for (const data of datas) {
    for (const produto of produtos) {
      for (const unidade of unidades) {
        const base = VOLUME_BASE[produto.id] * PESO_UNIDADE[unidade.id];
        registros.push({
          id,
          data,
          produto: produto.nome,
          unidade: unidade.nome,
          quantidade: Math.max(3, Math.round(base * (1 + variacao(id)))),
        });
        id += 1;
      }
    }
  }

  return registros;
}

export const tabelaPreVisualizacao: RegistroImportado[] = gerarRegistros();
