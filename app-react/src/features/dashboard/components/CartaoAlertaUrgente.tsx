import { badgeUrgencia, cores, estiloUrgencia } from "@/styles/tokens";
import type { AlertaUrgente } from "@/domain/types";

export function CartaoAlertaUrgente({ alerta }: { alerta: AlertaUrgente }) {
  const estilo = estiloUrgencia[alerta.urgencia];

  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-1"
      style={{ background: cores.fundo, border: `1px solid ${cores.borda}` }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: cores.texto }}>
          {alerta.produto}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full" style={badgeUrgencia(alerta.urgencia)}>
          {estilo.label}
        </span>
      </div>

      <p className="text-xs" style={{ color: cores.textoSuave }}>
        {alerta.unidade}
      </p>

      <div className="flex items-center justify-between">
        <span className="text-xs" style={{ color: cores.textoSuave }}>
          Em estoque: <strong style={{ color: cores.texto }}>{alerta.estoque}</strong> (mín. {alerta.minimo})
        </span>
        <span
          className="text-xs"
          style={{ color: alerta.urgencia === "critico" ? estiloUrgencia.critico.cor : cores.textoSuave }}
        >
          repor em {alerta.prazo}
        </span>
      </div>
    </div>
  );
}
