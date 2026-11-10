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

/** Previsão gerada (status `trained`); o acerto no teste do treino aparece nos indicadores e
 *  nos relatórios. */
const comPrevisao: EstiloStatus = {
  label: "Com previsão",
  explicacao: "A previsão foi gerada. O acerto no teste do treino está nos indicadores.",
  cor: "#1a6b3c",
  fundo: "#e8f5e0",
  borda: "#b4dbb4",
};

/** Status da previsão de cada categoria e produto de grama, em linguagem da loja. */
export const estiloStatus: Record<StatusModelo, EstiloStatus> = {
  trained: comPrevisao,
  insufficient_data: {
    label: "Poucos dados",
    explicacao: "Vendeu pouco para prever: menos de 180 dias de histórico ou, no produto, venda em poucos dias do último ano.",
    cor: "#d4183d",
    fundo: "#fff0f3",
    borda: "#f5c2cc",
  },
  error: {
    label: "Sem previsão",
    explicacao: "O cálculo desta previsão falhou no último treino. Treine de novo; se continuar, avise a equipe do projeto.",
    cor: "#a12622",
    fundo: "#fdecea",
    borda: "#f5c2bf",
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
