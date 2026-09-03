import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { estiloUrgencia } from "@/styles/tokens";

export function EstadoErro({ mensagem, aoTentarNovamente }: { mensagem: string; aoTentarNovamente?: () => void }) {
  const estilo = estiloUrgencia.critico;

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center" role="alert">
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center"
        style={{ background: estilo.fundo }}
      >
        <AlertTriangle size={20} style={{ color: estilo.cor }} />
      </div>
      <p className="text-sm max-w-sm" style={{ color: "var(--foreground)" }}>
        {mensagem}
      </p>
      {aoTentarNovamente && (
        <Button variant="outline" size="sm" className="gap-2" onClick={aoTentarNovamente}>
          <RefreshCw size={14} />
          Tentar de novo
        </Button>
      )}
    </div>
  );
}
