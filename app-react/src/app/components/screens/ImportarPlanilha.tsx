import { useState, useRef, useCallback } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, Loader2, Sparkles, X } from "lucide-react";
import { Card, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import { useNavigate } from "react-router";
import { dados, unidades } from "../../data/mockData";
import { formatarMesAno, formatarNumero } from "@/lib/format";

const arquivos = dados.importacao.arquivos;
const lojasConfiaveis = unidades.filter((u) => u.modelo.status === "trained").length;

const steps = [
  { id: 1, label: "Enviar arquivo" },
  { id: 2, label: "Verificando" },
  { id: 3, label: "Calculando" },
  { id: 4, label: "Pronto!" },
];

type StepStatus = "pending" | "active" | "done";

function stepStatus(step: number, current: number): StepStatus {
  if (step < current) return "done";
  if (step === current) return "active";
  return "pending";
}

export function ImportarPlanilha() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<{ name: string; size: string } | null>(null);
  const [progress, setProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    const sizeMB = (f.size / 1024 / 1024).toFixed(2);
    setFile({ name: f.name, size: `${sizeMB} MB` });
    setCurrentStep(2);
    simulateProgress();
  };

  const simulateProgress = () => {
    setProcessing(true);
    setProgress(0);
    let p = 0;
    const iv = setInterval(() => {
      p += Math.random() * 18 + 5;
      if (p >= 100) {
        p = 100;
        clearInterval(iv);
        setProgress(100);
        setTimeout(() => {
          setProcessing(false);
          setCurrentStep(3);
          setTimeout(() => setCurrentStep(4), 1800);
        }, 400);
      }
      setProgress(Math.min(p, 100));
    }, 200);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const reset = () => {
    setFile(null);
    setCurrentStep(1);
    setProgress(0);
    setProcessing(false);
  };

  return (
    <div className="p-6 flex flex-col gap-6 max-w-3xl mx-auto">
      {/* Stepper */}
      <div className="flex items-center gap-0">
        {steps.map((step, idx) => {
          const status = stepStatus(step.id, currentStep);
          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-sm transition-colors"
                  style={{
                    background:
                      status === "done"
                        ? "var(--primary)"
                        : status === "active"
                        ? "var(--primary)"
                        : "var(--muted)",
                    color:
                      status === "pending" ? "var(--muted-foreground)" : "#fff",
                    fontWeight: 600,
                  }}
                >
                  {status === "done" ? <CheckCircle2 size={18} /> : step.id}
                </div>
                <span
                  className="text-xs whitespace-nowrap"
                  style={{
                    color:
                      status === "active" ? "var(--primary)" : "var(--muted-foreground)",
                    fontWeight: status === "active" ? 600 : 400,
                  }}
                >
                  {step.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className="flex-1 h-0.5 mb-6 mx-1"
                  style={{
                    background: step.id < currentStep ? "var(--primary)" : "var(--border)",
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Main content */}
      {currentStep === 1 && (
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-8">
            <div
              className="border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-4 py-16 px-8 cursor-pointer transition-colors"
              style={{
                borderColor: dragging ? "var(--primary)" : "rgba(26,107,60,0.3)",
                background: dragging ? "var(--secondary)" : "var(--background)",
              }}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--secondary)" }}
              >
                <Upload size={28} style={{ color: "var(--primary)" }} />
              </div>
              <div className="text-center">
                <p className="text-base mb-1" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                  Arraste e solte sua planilha aqui
                </p>
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  ou clique para selecionar o arquivo
                </p>
              </div>
              <div className="flex gap-2">
                {[".xlsx", ".csv"].map((ext) => (
                  <span
                    key={ext}
                    className="text-xs px-3 py-1 rounded-full"
                    style={{
                      background: "var(--accent)",
                      color: "var(--accent-foreground)",
                      fontWeight: 500,
                    }}
                  >
                    {ext}
                  </span>
                ))}
              </div>
              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                Relatório “Contas a Receber” do sistema da loja, um arquivo por mês · até 50 MB
              </p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
          </CardContent>
        </Card>
      )}

      {currentStep === 2 && file && (
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-8 flex flex-col gap-5">
            <div className="flex items-start gap-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--secondary)" }}
              >
                <FileSpreadsheet size={24} style={{ color: "var(--primary)" }} />
              </div>
              <div className="flex-1">
                <p className="text-sm mb-0.5" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                  {file.name}
                </p>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  {file.size} · Verificando se o arquivo está correto...
                </p>
              </div>
              <button onClick={reset} className="text-muted-foreground hover:opacity-70">
                <X size={18} />
              </button>
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs" style={{ color: "var(--muted-foreground)" }}>
                <span>Validando estrutura e dados...</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
            {processing && (
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
                <Loader2 size={15} className="animate-spin" />
                Conferindo colunas, datas e quantidades...
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {currentStep === 3 && (
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-8 flex flex-col items-center gap-5">
            <Loader2 size={40} className="animate-spin" style={{ color: "var(--primary)" }} />
            <div className="text-center">
              <p className="text-base mb-1" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                Calculando as previsões...
              </p>
              <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                O sistema está estimando a demanda para todos os produtos
              </p>
            </div>
            <Progress value={65} className="w-full h-2" />
          </CardContent>
        </Card>
      )}

      {currentStep === 4 && (
        <Card className="border" style={{ borderColor: "var(--border)", background: "var(--secondary)" }}>
          <CardContent className="p-8 flex flex-col items-center gap-5">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{ background: "var(--primary)" }}
            >
              <Sparkles size={28} color="#fff" />
            </div>
            <div className="text-center">
              <p className="text-lg mb-1" style={{ color: "var(--foreground)", fontWeight: 700 }}>
                Previsões calculadas com sucesso!
              </p>
              <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                {formatarNumero(dados.base.skus)} produtos · {unidades.length} lojas · próximos {dados.configuracao.horizonte_dias} dias
              </p>
            </div>
            <div className="grid grid-cols-3 gap-4 w-full">
              {[
                { label: "Vendas analisadas", value: formatarNumero(dados.base.linhas) },
                { label: "Período coberto", value: `${formatarMesAno(dados.base.inicio)} a ${formatarMesAno(dados.base.fim)}` },
                { label: "Lojas com previsão confiável", value: `${lojasConfiaveis} de ${unidades.length}` },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-lg p-4 text-center"
                  style={{ background: "#fff", border: "1px solid var(--border)" }}
                >
                  <p className="text-xl mb-0.5" style={{ color: "var(--primary)", fontWeight: 700 }}>
                    {stat.value}
                  </p>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    {stat.label}
                  </p>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={reset}>
                Enviar outro arquivo
              </Button>
              <Button style={{ background: "var(--primary)", color: "#fff" }} onClick={() => navigate("/previsao")}>
                Ver a previsão →
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardContent className="p-5 flex flex-col gap-3">
          <div className="flex items-baseline justify-between gap-2 flex-wrap">
            <p className="text-sm" style={{ fontWeight: 600 }}>
              Planilhas já carregadas
            </p>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {arquivos.length} meses · {formatarNumero(arquivos.reduce((s, a) => s + a.registros, 0))} linhas · nenhuma duplicada
            </p>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 lg:grid-cols-9 gap-2">
            {arquivos.map((a) => (
              <div
                key={a.arquivo}
                className="rounded-md px-2 py-1.5 text-center"
                style={{ background: "var(--secondary)", border: "1px solid var(--border)" }}
                title={`${a.arquivo} · ${formatarNumero(a.registros)} linhas · assinatura ${a.hash.slice(0, 8)}`}
              >
                <p className="text-xs" style={{ fontWeight: 600, color: "var(--secondary-foreground)" }}>
                  {formatarMesAno(a.competencia)}
                </p>
                <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                  {formatarNumero(a.registros)}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
