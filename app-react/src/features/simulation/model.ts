import type { PontoSimulacao } from "@/domain/types";

const ELASTICIDADE_DESCONTO = 1.8;
const MARGEM_SOBRE_INCREMENTO = 0.62;
const CUSTO_DO_DESCONTO = 0.8;

export type NivelSinergia = "baixa" | "media" | "alta";

export interface Sinergia {
  nivel: NivelSinergia;
  taxaAceitacao: number;
  fator: number;
}

const SINERGIAS: Record<string, Sinergia> = {
  "rosa-branca": { nivel: "baixa", taxaAceitacao: 0.12, fator: 0.05 },
  girassol: { nivel: "media", taxaAceitacao: 0.22, fator: 0.1 },
  lirio: { nivel: "media", taxaAceitacao: 0.2, fator: 0.09 },
  orquidea: { nivel: "alta", taxaAceitacao: 0.32, fator: 0.16 },
  "buque-misto": { nivel: "alta", taxaAceitacao: 0.35, fator: 0.18 },
};

const SINERGIA_PADRAO: Sinergia = { nivel: "media", taxaAceitacao: 0.2, fator: 0.1 };

export const NENHUM_COMPLEMENTO = "nenhum";

export function sinergiaDe(complementoId: string): Sinergia | null {
  if (complementoId === NENHUM_COMPLEMENTO) return null;
  return SINERGIAS[complementoId] ?? SINERGIA_PADRAO;
}

export interface ParametrosCenario {
  descontoPercentual: number;
  complementoId: string;
}

export interface PontoCenario extends PontoSimulacao {
  comPromo: number;
}

export interface ResultadoCenario {
  pontos: PontoCenario[];
  totalSemPromo: number;
  totalComPromo: number;
  variacaoUnidades: number;
  variacaoRelativa: number;
  impactoMargem: number;
  sinergia: Sinergia | null;
}

export function simularCenario(
  base: readonly PontoSimulacao[],
  { descontoPercentual, complementoId }: ParametrosCenario,
): ResultadoCenario {
  const sinergia = sinergiaDe(complementoId);
  const desconto = descontoPercentual / 100;
  const fator = 1 + desconto * ELASTICIDADE_DESCONTO + (sinergia?.fator ?? 0);

  const pontos = base.map((ponto) => ({
    ...ponto,
    comPromo: Math.round(ponto.semPromo * fator),
  }));

  const totalSemPromo = pontos.reduce((soma, ponto) => soma + ponto.semPromo, 0);
  const totalComPromo = pontos.reduce((soma, ponto) => soma + ponto.comPromo, 0);
  const variacaoUnidades = totalComPromo - totalSemPromo;

  return {
    pontos,
    totalSemPromo,
    totalComPromo,
    variacaoUnidades,
    variacaoRelativa: totalSemPromo === 0 ? 0 : variacaoUnidades / totalSemPromo,
    impactoMargem: Math.round(
      variacaoUnidades * MARGEM_SOBRE_INCREMENTO - totalComPromo * desconto * CUSTO_DO_DESCONTO,
    ),
    sinergia,
  };
}

export type FaixaDesconto = "moderado" | "equilibrado" | "agressivo";

export function faixaDe(descontoPercentual: number): FaixaDesconto {
  if (descontoPercentual <= 15) return "moderado";
  if (descontoPercentual <= 25) return "equilibrado";
  return "agressivo";
}

export function recomendacao(
  resultado: ResultadoCenario,
  descontoPercentual: number,
  nomeComplemento: string,
): string {
  const variacao = (resultado.variacaoRelativa * 100).toFixed(1).replace(".", ",");
  const { sinergia } = resultado;

  switch (faixaDe(descontoPercentual)) {
    case "moderado":
      return (
        `Desconto de ${descontoPercentual}% é moderado — as vendas devem crescer ${variacao}% ` +
        `sem prejudicar muito o lucro.` +
        (sinergia
          ? ` Combinar com ${nomeComplemento} pode aumentar o ticket médio com boa aceitação.`
          : " Boa opção para semanas comuns.")
      );
    case "equilibrado":
      return (
        `Desconto de ${descontoPercentual}% equilibra bem o aumento de vendas e o lucro.` +
        (sinergia
          ? ` O combo com ${nomeComplemento} deve ser aceito por cerca de ${Math.round(sinergia.taxaAceitacao * 100)}% dos clientes, elevando ainda mais o resultado.`
          : " Ótimo para datas especiais como Dia das Mães e Natal.")
      );
    case "agressivo":
      return (
        `Desconto de ${descontoPercentual}% vende muito mais, mas o lucro por unidade cai bastante.` +
        (sinergia
          ? ` Adicionar ${nomeComplemento} ao combo ajuda a recuperar margem pelo ticket maior.`
          : " Use apenas em produtos com muito estoque parado ou alta saída.")
      );
  }
}
