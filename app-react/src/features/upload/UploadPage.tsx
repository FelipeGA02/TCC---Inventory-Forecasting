import { useCallback, useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router";
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Loader2, Sparkles, Upload, X } from "lucide-react";
import { Card, CardContent } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Progress } from "@/app/components/ui/progress";
import { formatarNumero } from "@/lib/format";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { ETAPAS, useUploadPlanilha, type EtapaUpload } from "./hooks";

type StatusEtapa = "pendente" | "atual" | "concluida";

const ORDEM: EtapaUpload[] = ["escolher", "enviando", "calculando", "concluido"];

function statusDaEtapa(etapa: EtapaUpload, atual: EtapaUpload): StatusEtapa {
  const indiceAtual = atual === "erro" ? 0 : ORDEM.indexOf(atual);
  const indice = ORDEM.indexOf(etapa);
  if (indice < indiceAtual) return "concluida";
  if (indice === indiceAtual) return "atual";
  return "pendente";
}

export function UploadPage() {
  const { etapa, arquivo, resultado, erro, enviar, reiniciar } = useUploadPlanilha();
  const [arrastando, setArrastando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navegar = useNavigate();

  const aoSoltar = useCallback(
    (evento: DragEvent) => {
      evento.preventDefault();
      setArrastando(false);
      const selecionado = evento.dataTransfer.files[0];
      if (selecionado) void enviar(selecionado);
    },
    [enviar],
  );

  return (
    <div className="p-6 flex flex-col gap-6 max-w-3xl mx-auto">
      <ol className="flex items-center gap-0" aria-label="Etapas do envio">
        {ETAPAS.map((passo, indice) => {
          const status = statusDaEtapa(passo.etapa, etapa);
          return (
            <li key={passo.etapa} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-sm transition-colors"
                  style={{
                    background: status === "pendente" ? "var(--muted)" : cores.primaria,
                    color: status === "pendente" ? cores.textoSuave : "#fff",
                    fontWeight: 600,
                  }}
                >
                  {status === "concluida" ? <CheckCircle2 size={18} /> : indice + 1}
                </div>
                <span
                  className="text-xs whitespace-nowrap"
                  style={{
                    color: status === "atual" ? cores.primaria : cores.textoSuave,
                    fontWeight: status === "atual" ? 600 : 400,
                  }}
                >
                  {passo.label}
                </span>
              </div>
              {indice < ETAPAS.length - 1 && (
                <div
                  className="flex-1 h-0.5 mb-6 mx-1"
                  style={{ background: status === "concluida" ? cores.primaria : cores.borda }}
                />
              )}
            </li>
          );
        })}
      </ol>

      {(etapa === "escolher" || etapa === "erro") && (
        <Card className="border" style={{ borderColor: cores.borda }}>
          <CardContent className="p-8 flex flex-col gap-5">
            {erro && (
              <div
                className="rounded-lg px-4 py-3 flex items-start gap-2 text-sm"
                role="alert"
                style={{
                  background: estiloUrgencia.critico.fundo,
                  border: `1px solid ${estiloUrgencia.critico.borda}`,
                  color: estiloUrgencia.critico.cor,
                }}
              >
                <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
                <div>
                  {arquivo && <strong className="block">{arquivo.nome}</strong>}
                  {erro}
                </div>
              </div>
            )}

            <div
              role="button"
              tabIndex={0}
              className="border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-4 py-16 px-8 cursor-pointer transition-colors"
              style={{
                borderColor: arrastando ? cores.primaria : "rgba(26,107,60,0.3)",
                background: arrastando ? "var(--secondary)" : cores.fundo,
              }}
              onDragOver={(evento) => {
                evento.preventDefault();
                setArrastando(true);
              }}
              onDragLeave={() => setArrastando(false)}
              onDrop={aoSoltar}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(evento) => {
                if (evento.key === "Enter" || evento.key === " ") inputRef.current?.click();
              }}
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--secondary)" }}
              >
                <Upload size={28} style={{ color: cores.primaria }} />
              </div>
              <div className="text-center">
                <p className="text-base mb-1" style={{ color: cores.texto, fontWeight: 600 }}>
                  Arraste e solte sua planilha aqui
                </p>
                <p className="text-sm" style={{ color: cores.textoSuave }}>
                  ou clique para selecionar o arquivo
                </p>
              </div>
              <span
                className="text-xs px-3 py-1 rounded-full"
                style={{ background: "var(--accent)", color: "var(--accent-foreground)", fontWeight: 500 }}
              >
                .xlsx
              </span>
              <p className="text-xs" style={{ color: cores.textoSuave }}>
                Tamanho máximo: 50 MB
              </p>
            </div>

            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(evento) => {
                const selecionado = evento.target.files?.[0];
                if (selecionado) void enviar(selecionado);
                evento.target.value = "";
              }}
            />
          </CardContent>
        </Card>
      )}

      {etapa === "enviando" && arquivo && (
        <Card className="border" style={{ borderColor: cores.borda }}>
          <CardContent className="p-8 flex flex-col gap-5">
            <div className="flex items-start gap-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--secondary)" }}
              >
                <FileSpreadsheet size={24} style={{ color: cores.primaria }} />
              </div>
              <div className="flex-1">
                <p className="text-sm mb-0.5" style={{ color: cores.texto, fontWeight: 600 }}>
                  {arquivo.nome}
                </p>
                <p className="text-xs" style={{ color: cores.textoSuave }}>
                  {arquivo.tamanho} · enviando e conferindo colunas, datas e quantidades…
                </p>
              </div>
              <button
                type="button"
                onClick={reiniciar}
                aria-label="Cancelar envio"
                className="text-muted-foreground hover:opacity-70"
              >
                <X size={18} />
              </button>
            </div>

            <Progress className="h-2" />
            <div className="flex items-center gap-2 text-sm" style={{ color: cores.textoSuave }}>
              <Loader2 size={15} className="animate-spin" />
              Isso pode levar alguns minutos em planilhas grandes.
            </div>
          </CardContent>
        </Card>
      )}

      {etapa === "calculando" && (
        <Card className="border" style={{ borderColor: cores.borda }}>
          <CardContent className="p-8 flex flex-col items-center gap-5">
            <Loader2 size={40} className="animate-spin" style={{ color: cores.primaria }} />
            <div className="text-center">
              <p className="text-base mb-1" style={{ color: cores.texto, fontWeight: 600 }}>
                Calculando as previsões…
              </p>
              <p className="text-sm" style={{ color: cores.textoSuave }}>
                O sistema está estimando a demanda para todos os produtos
              </p>
            </div>
            <Progress className="w-full h-2" />
          </CardContent>
        </Card>
      )}

      {etapa === "concluido" && resultado && (
        <Card className="border" style={{ borderColor: cores.borda, background: "var(--secondary)" }}>
          <CardContent className="p-8 flex flex-col items-center gap-5">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{ background: cores.primaria }}
            >
              <Sparkles size={28} color="#fff" />
            </div>

            <div className="text-center">
              <p className="text-lg mb-1" style={{ color: cores.texto, fontWeight: 700 }}>
                {resultado.duplicado
                  ? "Esta planilha já tinha sido enviada"
                  : "Previsões calculadas com sucesso!"}
              </p>
              <p className="text-sm" style={{ color: cores.textoSuave }}>
                {resultado.duplicado
                  ? "Nada foi duplicado na base. Você pode enviar outro arquivo."
                  : `${resultado.arquivo} · dados atualizados`}
              </p>
            </div>

            {!resultado.duplicado && (
              <div className="grid grid-cols-2 gap-4 w-full">
                {[
                  { label: "Vendas registradas", valor: formatarNumero(resultado.linhasLidas) },
                  { label: "Linhas ignoradas", valor: formatarNumero(resultado.linhasIgnoradas) },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-lg p-4 text-center"
                    style={{ background: "#fff", border: `1px solid ${cores.borda}` }}
                  >
                    <p className="text-xl mb-0.5" style={{ color: cores.primaria, fontWeight: 700 }}>
                      {item.valor}
                    </p>
                    <p className="text-xs" style={{ color: cores.textoSuave }}>
                      {item.label}
                    </p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={reiniciar}>
                Enviar outro arquivo
              </Button>
              <Button
                style={{ background: cores.primaria, color: "#fff" }}
                onClick={() => navegar("/previsao")}
              >
                Ver quanto comprar →
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
