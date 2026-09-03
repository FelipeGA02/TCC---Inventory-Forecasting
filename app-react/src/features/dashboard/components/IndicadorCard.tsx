import { AlertTriangle, ArrowDownRight, ArrowUpRight, Brain, Clock, Package, type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/app/components/ui/card";
import { cores, estiloUrgencia } from "@/styles/tokens";
import type { IndicadorDashboard } from "@/domain/types";

const APARENCIA: Record<IndicadorDashboard["chave"], { icone: LucideIcon; cor: string; fundo: string }> = {
  "estoque-critico": { icone: AlertTriangle, cor: estiloUrgencia.critico.cor, fundo: estiloUrgencia.critico.fundo },
  mape: { icone: Brain, cor: estiloUrgencia.ok.cor, fundo: estiloUrgencia.ok.fundo },
  "produtos-monitorados": { icone: Package, cor: estiloUrgencia.ok.cor, fundo: estiloUrgencia.ok.fundo },
  "proximo-calculo": { icone: Clock, cor: estiloUrgencia.atencao.cor, fundo: estiloUrgencia.atencao.fundo },
};

export function IndicadorCard({ indicador }: { indicador: IndicadorDashboard }) {
  const { icone: Icone, cor, fundo } = APARENCIA[indicador.chave];

  return (
    <Card className="border" style={{ borderColor: cores.borda }}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: fundo }}>
            <Icone size={20} color={cor} />
          </div>

          {indicador.tendencia === "alta" && indicador.ajuda && (
            <span className="flex items-center gap-0.5 text-xs" style={{ color: estiloUrgencia.critico.cor }}>
              <ArrowUpRight size={13} />
              {indicador.ajuda}
            </span>
          )}
          {indicador.tendencia === "baixa" && (
            <span className="flex items-center gap-0.5 text-xs" style={{ color: estiloUrgencia.ok.cor }}>
              <ArrowDownRight size={13} />
              <span>melhorou vs. semana ant.</span>
            </span>
          )}
        </div>

        <p className="text-3xl mb-0.5" style={{ color: cores.texto, fontWeight: 700, lineHeight: 1 }}>
          {indicador.valor}
        </p>
        <p className="text-sm" style={{ color: cores.textoSuave }} title={indicador.ajuda}>
          {indicador.descricao}
        </p>
        {indicador.tendencia === "neutra" && indicador.ajuda && (
          <p className="text-xs mt-1" style={{ color: cores.textoSuave }}>
            {indicador.ajuda}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
