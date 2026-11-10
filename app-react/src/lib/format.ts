const numero = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const numeroDecimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const percentual = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const formatarNumero = (valor: number): string => numero.format(valor);

/** Quantidade com 1 casa só quando ela importa (valores pequenos, ex.: 0,4 m²). */
export const formatarQtd = (valor: number): string =>
  Math.abs(valor) < 10 && valor % 1 !== 0 ? numeroDecimal.format(valor) : numero.format(valor);

export const formatarMoeda = (valor: number): string => moeda.format(valor);

/** R$ 52,9 mi · R$ 318 mil · R$ 940 — para eixos e indicadores. */
export function formatarMoedaCompacta(valor: number): string {
  const abs = Math.abs(valor);
  const fmt = (v: number, casas: number) => v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  if (abs >= 1e6) return `R$ ${fmt(valor / 1e6, 1)} mi`;
  if (abs >= 1e3) return `R$ ${fmt(valor / 1e3, 0)} mil`;
  return `R$ ${fmt(valor, 0)}`;
}

export const formatarPercentual = (fracao: number): string => percentual.format(fracao);

export const formatarDecimal = (valor: number, casas = 2): string =>
  valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function partes(iso: string): [number, number, number] {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return [a ?? 0, m ?? 1, d ?? 1];
}

/** "2026-03-02" → "02/03". */
export function formatarDiaMes(iso: string): string {
  const [, m, d] = partes(iso);
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
}

/** "2026-03-02" → "02/03/2026". */
export function formatarData(iso: string): string {
  const [a, m, d] = partes(iso);
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${a}`;
}

/** "2026-03-02" → "2 mar". */
export function formatarDiaMesCurto(iso: string): string {
  const [, m, d] = partes(iso);
  return `${d} ${MESES[m - 1]}`;
}

/** "2026-02" ou "2026-02-09" → "fev/26". */
export function formatarMesAno(iso: string): string {
  const [a, m] = partes(iso.length === 7 ? `${iso}-01` : iso);
  return `${MESES[m - 1]}/${String(a).slice(2)}`;
}

export function pluralizar(quantidade: number, singular: string, plural = `${singular}s`): string {
  return `${formatarNumero(quantidade)} ${quantidade === 1 ? singular : plural}`;
}
