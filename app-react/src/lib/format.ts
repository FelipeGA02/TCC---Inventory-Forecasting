const numero = new Intl.NumberFormat("pt-BR");
const percentual = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const formatarNumero = (valor: number): string => numero.format(valor);

export const formatarPercentual = (fracao: number): string => percentual.format(fracao);

export function formatarTamanhoArquivo(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function pluralizar(quantidade: number, singular: string, plural = `${singular}s`): string {
  return `${formatarNumero(quantidade)} ${quantidade === 1 ? singular : plural}`;
}
