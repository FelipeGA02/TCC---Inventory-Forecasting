import type { LucideIcon } from "lucide-react";
import { cores } from "@/styles/tokens";

export function EstadoVazio({
  icone: Icone,
  titulo,
  descricao,
}: {
  icone: LucideIcon;
  titulo: string;
  descricao?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center mb-1"
        style={{ background: "var(--muted)" }}
      >
        <Icone size={20} style={{ color: cores.textoSuave }} />
      </div>
      <p className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
        {titulo}
      </p>
      {descricao && (
        <p className="text-xs max-w-xs" style={{ color: cores.textoSuave }}>
          {descricao}
        </p>
      )}
    </div>
  );
}
