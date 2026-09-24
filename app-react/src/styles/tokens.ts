import type { Urgencia } from "@/domain/types";

export const cores = {
  primaria: "var(--primary)",
  destaque: "var(--destructive)",
  atencao: "#f0a500",
  sucesso: "#1a6b3c",
  texto: "var(--foreground)",
  textoSuave: "var(--muted-foreground)",
  borda: "var(--border)",
  fundo: "var(--background)",
  cartao: "var(--card)",
} as const;

export const coresGrafico = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const;

export interface EstiloUrgencia {
  label: string;
  cor: string;
  fundo: string;
  borda: string;
}

export const estiloUrgencia: Record<Urgencia, EstiloUrgencia> = {
  critico: { label: "Crítico", cor: "#d4183d", fundo: "#fff0f3", borda: "#f5c2cc" },
  atencao: { label: "Atenção", cor: "#b77800", fundo: "#fff8e1", borda: "#ffe0a0" },
  ok: { label: "OK", cor: "#1a6b3c", fundo: "#e8f5e0", borda: "#b4dbb4" },
};

export function badgeUrgencia(urgencia: Urgencia): React.CSSProperties {
  const estilo = estiloUrgencia[urgencia];
  return { background: estilo.fundo, color: estilo.cor, border: `1px solid ${estilo.borda}` };
}
