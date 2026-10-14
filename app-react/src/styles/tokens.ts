import type { StatusModelo } from "@/domain/types";

export const cores = {
  primaria: "var(--primary)",
  destaque: "var(--destructive)",
  atencao: "#b77800",
  sucesso: "#1a6b3c",
  texto: "var(--foreground)",
  textoSuave: "var(--muted-foreground)",
  borda: "var(--border)",
  fundo: "var(--background)",
  cartao: "var(--card)",
} as const;

export interface EstiloStatus {
  label: string;
  explicacao: string;
  cor: string;
  fundo: string;
  borda: string;
}

/** Status do modelo L1 em linguagem da loja (CLAUDE.md, limiares de qualidade). */
export const estiloStatus: Record<StatusModelo, EstiloStatus> = {
  trained: {
    label: "Confiável",
    explicacao: "Passou nos testes de acerto: erra menos que repetir a semana passada e a faixa acerta ~95% dos dias.",
    cor: "#1a6b3c",
    fundo: "#e8f5e0",
    borda: "#b4dbb4",
  },
  low_confidence: {
    label: "Use com cautela",
    explicacao: "A previsão é gerada, mas não passou em todos os testes de acerto. Confira a faixa antes de decidir.",
    cor: "#8a5a00",
    fundo: "#fff8e1",
    borda: "#ffe0a0",
  },
  insufficient_data: {
    label: "Poucos dados",
    explicacao: "A loja tem menos de 180 dias de vendas: ainda não dá para prever.",
    cor: "#d4183d",
    fundo: "#fff0f3",
    borda: "#f5c2cc",
  },
  training: {
    label: "Calculando",
    explicacao: "O sistema está recalculando a previsão.",
    cor: "#5a7260",
    fundo: "#eef6ea",
    borda: "#cfe3c8",
  },
};

export function badgeStatus(status: StatusModelo): React.CSSProperties {
  const estilo = estiloStatus[status];
  return { background: estilo.fundo, color: estilo.cor, border: `1px solid ${estilo.borda}` };
}

export const estiloTooltip: React.CSSProperties = {
  background: "#fff",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "0 4px 12px rgba(26,46,30,0.08)",
};

export const eixo = { fontSize: 11, fill: "var(--muted-foreground)" } as const;
