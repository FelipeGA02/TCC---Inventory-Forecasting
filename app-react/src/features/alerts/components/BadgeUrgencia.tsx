import { AlertTriangle, CheckCircle2, XCircle, type LucideIcon } from "lucide-react";
import { badgeUrgencia, estiloUrgencia } from "@/styles/tokens";
import type { Urgencia } from "@/domain/types";

const ICONE: Record<Urgencia, LucideIcon> = {
  critico: XCircle,
  atencao: AlertTriangle,
  ok: CheckCircle2,
};

export const fundoLinha: Record<Urgencia, string | undefined> = {
  critico: "#fffafb",
  atencao: "#fffdf4",
  ok: undefined,
};

export function BadgeUrgencia({ urgencia }: { urgencia: Urgencia }) {
  const Icone = ICONE[urgencia];
  const estilo = estiloUrgencia[urgencia];

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
      style={badgeUrgencia(urgencia)}
    >
      <Icone size={13} color={estilo.cor} />
      {estilo.label}
    </span>
  );
}

export { ICONE as iconeUrgencia };
