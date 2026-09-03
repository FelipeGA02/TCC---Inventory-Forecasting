import type {
  AlertaReposicao,
  AlertaUrgente,
  IndicadorDashboard,
  LinhaPrevisaoSemanal,
  PontoPrevisao,
  PontoSimulacao,
  PontoTendencia,
  Produto,
  RegistroImportado,
  EventoSazonal,
  MetricaModelo,
  RelatorioGerado,
  Unidade,
} from "@/domain/types";

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

export const alertasUrgentes: AlertaUrgente[] = [
  { id: 1, produto: "Rosa Vermelha", unidade: "Centro", estoque: 48, minimo: 180, prazo: "1 dia", urgencia: "critico" },
  { id: 2, produto: "Buquê Misto", unidade: "Jardim Canadá", estoque: 22, minimo: 90, prazo: "1 dia", urgencia: "critico" },
  { id: 3, produto: "Lírio Branco", unidade: "Itabirito", estoque: 35, minimo: 110, prazo: "2 dias", urgencia: "critico" },
  { id: 4, produto: "Girassol", unidade: "Centro", estoque: 96, minimo: 120, prazo: "4 dias", urgencia: "atencao" },
  { id: 5, produto: "Orquídea Phalaenopsis", unidade: "Jardim Canadá", estoque: 41, minimo: 55, prazo: "5 dias", urgencia: "atencao" },
  { id: 6, produto: "Rosa Branca", unidade: "Itabirito", estoque: 88, minimo: 100, prazo: "6 dias", urgencia: "atencao" },
  { id: 7, produto: "Crisântemo Amarelo", unidade: "Centro", estoque: 210, minimo: 130, prazo: "12 dias", urgencia: "ok" },
  { id: 8, produto: "Tulipa Holandesa", unidade: "Jardim Canadá", estoque: 164, minimo: 70, prazo: "15 dias", urgencia: "ok" },
];

export const alertasReposicao: AlertaReposicao[] = [
  { id: 1, produto: "Rosa Vermelha", grupo: "Rosas", unidade: "Centro", estoqueAtual: 48, estoqueMinimo: 180, qtdRecomendada: 260, prazo: "1 dia", urgencia: "critico" },
  { id: 2, produto: "Buquê Misto", grupo: "Rosas", unidade: "Jardim Canadá", estoqueAtual: 22, estoqueMinimo: 90, qtdRecomendada: 130, prazo: "1 dia", urgencia: "critico" },
  { id: 3, produto: "Lírio Branco", grupo: "Lírios", unidade: "Itabirito", estoqueAtual: 35, estoqueMinimo: 110, qtdRecomendada: 150, prazo: "2 dias", urgencia: "critico" },
  { id: 4, produto: "Rosa Vermelha", grupo: "Rosas", unidade: "Itabirito", estoqueAtual: 62, estoqueMinimo: 140, qtdRecomendada: 190, prazo: "2 dias", urgencia: "critico" },
  { id: 5, produto: "Orquídea Phalaenopsis", grupo: "Orquídeas", unidade: "Centro", estoqueAtual: 18, estoqueMinimo: 60, qtdRecomendada: 75, prazo: "3 dias", urgencia: "critico" },
  { id: 6, produto: "Girassol", grupo: "Tropicais", unidade: "Centro", estoqueAtual: 96, estoqueMinimo: 120, qtdRecomendada: 90, prazo: "4 dias", urgencia: "atencao" },
  { id: 7, produto: "Orquídea Phalaenopsis", grupo: "Orquídeas", unidade: "Jardim Canadá", estoqueAtual: 41, estoqueMinimo: 55, qtdRecomendada: 45, prazo: "5 dias", urgencia: "atencao" },
  { id: 8, produto: "Rosa Branca", grupo: "Rosas", unidade: "Itabirito", estoqueAtual: 88, estoqueMinimo: 100, qtdRecomendada: 70, prazo: "6 dias", urgencia: "atencao" },
  { id: 9, produto: "Tulipa Holandesa", grupo: "Bulbosas", unidade: "Centro", estoqueAtual: 52, estoqueMinimo: 65, qtdRecomendada: 55, prazo: "6 dias", urgencia: "atencao" },
  { id: 10, produto: "Lírio Branco", grupo: "Lírios", unidade: "Jardim Canadá", estoqueAtual: 104, estoqueMinimo: 125, qtdRecomendada: 85, prazo: "7 dias", urgencia: "atencao" },
  { id: 11, produto: "Crisântemo Amarelo", grupo: "Crisântemos", unidade: "Itabirito", estoqueAtual: 71, estoqueMinimo: 85, qtdRecomendada: 60, prazo: "7 dias", urgencia: "atencao" },
  { id: 12, produto: "Girassol", grupo: "Tropicais", unidade: "Jardim Canadá", estoqueAtual: 118, estoqueMinimo: 130, qtdRecomendada: 80, prazo: "8 dias", urgencia: "atencao" },
  { id: 13, produto: "Crisântemo Amarelo", grupo: "Crisântemos", unidade: "Centro", estoqueAtual: 210, estoqueMinimo: 130, qtdRecomendada: 0, prazo: "12 dias", urgencia: "ok" },
  { id: 14, produto: "Tulipa Holandesa", grupo: "Bulbosas", unidade: "Jardim Canadá", estoqueAtual: 164, estoqueMinimo: 70, qtdRecomendada: 0, prazo: "15 dias", urgencia: "ok" },
  { id: 15, produto: "Rosa Branca", grupo: "Rosas", unidade: "Centro", estoqueAtual: 245, estoqueMinimo: 150, qtdRecomendada: 0, prazo: "16 dias", urgencia: "ok" },
  { id: 16, produto: "Girassol", grupo: "Tropicais", unidade: "Itabirito", estoqueAtual: 188, estoqueMinimo: 95, qtdRecomendada: 0, prazo: "18 dias", urgencia: "ok" },
  { id: 17, produto: "Buquê Misto", grupo: "Rosas", unidade: "Centro", estoqueAtual: 132, estoqueMinimo: 80, qtdRecomendada: 0, prazo: "19 dias", urgencia: "ok" },
  { id: 18, produto: "Lírio Branco", grupo: "Lírios", unidade: "Centro", estoqueAtual: 276, estoqueMinimo: 160, qtdRecomendada: 0, prazo: "21 dias", urgencia: "ok" },
];

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

export const tabelaPrevisaoSemanal: LinhaPrevisaoSemanal[] = [
  { semana: "Sem +1", recomendada: 620, total: 620 },
  { semana: "Sem +2", recomendada: 535, total: 1155 },
  { semana: "Sem +3", recomendada: 510, total: 1665 },
  { semana: "Sem +4", recomendada: 490, total: 2155 },
];

export const dadosSimulacaoBase: PontoSimulacao[] = [
  { dia: "Seg", semPromo: 42 },
  { dia: "Ter", semPromo: 38 },
  { dia: "Qua", semPromo: 51 },
  { dia: "Qui", semPromo: 64 },
  { dia: "Sex", semPromo: 96 },
  { dia: "Sáb", semPromo: 128 },
  { dia: "Dom", semPromo: 73 },
];

export const historicoRelatorios: RelatorioGerado[] = [
  { id: 1, nome: "Relatório completo — Junho", formato: "PDF", data: "22/06/2026 14:32", tamanho: "1,8 MB", usuario: "Gestora" },
  { id: 2, nome: "Lista de reposição — Centro", formato: "Excel", data: "22/06/2026 09:05", tamanho: "412 KB", usuario: "Gerente" },
  { id: 3, nome: "Quanto comprar — Semana 25", formato: "PDF", data: "21/06/2026 17:48", tamanho: "886 KB", usuario: "Gestora" },
  { id: 4, nome: "Qualidade das previsões", formato: "Excel", data: "19/06/2026 11:20", tamanho: "654 KB", usuario: "Gestora" },
  { id: 5, nome: "Simulações de promoções", formato: "PDF", data: "17/06/2026 16:09", tamanho: "1,1 MB", usuario: "Gerente" },
  { id: 6, nome: "Lista de reposição — Itabirito", formato: "Excel", data: "15/06/2026 08:54", tamanho: "388 KB", usuario: "Gerente" },
  { id: 7, nome: "Relatório completo — Maio", formato: "PDF", data: "01/06/2026 10:02", tamanho: "1,7 MB", usuario: "Gestora" },
];

const VOLUME_BASE: Record<string, number> = {
  "rosa-vermelha": 155,
  "rosa-branca": 92,
  lirio: 88,
  girassol: 76,
  orquidea: 34,
  crisantemo: 61,
  "buque-misto": 47,
};

const PESO_UNIDADE: Record<string, number> = {
  centro: 1,
  "jardim-canada": 0.72,
  itabirito: 0.55,
};

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
        const base = (VOLUME_BASE[produto.id] ?? 0) * (PESO_UNIDADE[unidade.id] ?? 0);
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

export const indicadoresDashboard: IndicadorDashboard[] = [
  {
    chave: "estoque-critico",
    valor: "3",
    descricao: "Produtos com Estoque Crítico",
    tendencia: "alta",
    ajuda: "+1 desde ontem",
  },
  {
    chave: "mape",
    valor: "7,4%",
    descricao: "Precisão das Previsões (MAPE)",
    tendencia: "baixa",
    ajuda: "MAPE: quanto as previsões erram em média. Quanto menor, melhor.",
  },
  {
    chave: "produtos-monitorados",
    valor: "142",
    descricao: "Produtos Monitorados",
    tendencia: "neutra",
    ajuda: "7 tipos, 3 lojas",
  },
  {
    chave: "proximo-calculo",
    valor: "2h 18m",
    descricao: "Próximo Cálculo Automático",
    tendencia: "neutra",
    ajuda: "Sáb, 24 Jun 08:00",
  },
];

export const metricasModelo: MetricaModelo[] = [
  { sigla: "MAE", valor: "31,4", explicacao: "Erro médio em unidades — o sistema erra ~31 un. por semana" },
  { sigla: "MAPE", valor: "7,4%", explicacao: "Precisão geral — quanto menor, mais o sistema acerta" },
  { sigla: "RMSE", valor: "38,7", explicacao: "Sensibilidade a erros grandes — penaliza desvios fortes" },
  { sigla: "R²", valor: "0,923", explicacao: "Confiança do modelo — explica 92% das variações de vendas" },
];

export const eventosSazonais: EventoSazonal[] = [
  { semana: "Sem +1", nome: "Festa Junina", impactoEsperado: 0.35 },
];
