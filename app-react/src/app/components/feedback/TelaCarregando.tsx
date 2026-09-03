import { Loader2 } from "lucide-react";
import { cores } from "@/styles/tokens";

export function TelaCarregando({ mensagem = "Carregando…" }: { mensagem?: string }) {
  return (
    <div
      className="h-full w-full flex flex-col items-center justify-center gap-3 py-16"
      style={{ background: cores.fundo }}
      role="status"
      aria-live="polite"
    >
      <Loader2 size={22} className="animate-spin" style={{ color: cores.primaria }} />
      <p className="text-sm" style={{ color: cores.textoSuave }}>
        {mensagem}
      </p>
    </div>
  );
}
