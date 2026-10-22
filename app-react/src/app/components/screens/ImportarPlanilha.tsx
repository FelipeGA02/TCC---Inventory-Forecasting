import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, Loader2, Sparkles, AlertTriangle, Lock } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import { useNavigate } from "react-router";
import { contexto } from "../../data/mockData";
import { api, type ResultadoUpload } from "../../data/api";
import { useDados } from "../../data/CarregarDados";
import { useAuth } from "../../auth/AuthContext";
import { ApiError, mensagemDoErro } from "@/lib/http/errors";
import { formatarMesAno, formatarNumero } from "@/lib/format";

const steps = [
  { id: 1, label: "Enviar arquivo" },
  { id: 2, label: "Conferindo e gravando" },
  { id: 3, label: "Pronto!" },
];

type StepStatus = "pending" | "active" | "done";

function stepStatus(step: number, current: number): StepStatus {
  if (step < current) return "done";
  if (step === current) return "active";
  return "pending";
}

// Resultado do último envio: sobrevive ao recarregamento das telas depois da carga
// (`recarregar()` monta as telas de novo com a lista de planilhas atualizada).
let ultimoResultado: ResultadoUpload | null = null;

function mensagemDeEnvio(erro: unknown): string {
  // 400 e 409 trazem a explicação da API (formato do arquivo, planilha repetida).
  if (erro instanceof ApiError && erro.detail && [400, 409, 413].includes(erro.status)) return erro.detail;
  return mensagemDoErro(erro);
}

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export function ImportarPlanilha() {
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const { recarregar } = useDados();
  const admin = usuario?.perfil === "admin";
  const arquivos = contexto.importacao.arquivos;

  const [resultado, setResultado] = useState<ResultadoUpload | null>(ultimoResultado);
  const [currentStep, setCurrentStep] = useState(ultimoResultado ? 3 : 1);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<{ name: string; size: string } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [proximoTreino, setProximoTreino] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (currentStep !== 3) return;
    api
      .statusModelos()
      .then((s) => setProximoTreino(s.next_retrain_at))
      .catch(() => setProximoTreino(null));
  }, [currentStep]);

  const handleFile = useCallback(
    (f: File) => {
      const sizeMB = (f.size / 1024 / 1024).toFixed(2);
      setFile({ name: f.name, size: `${sizeMB} MB` });
      setErro(null);
      setCurrentStep(2);
      api
        .enviarPlanilha(f)
        .then((r) => {
          ultimoResultado = r;
          setResultado(r);
          setCurrentStep(3);
          // atualiza a lista de planilhas e a base das telas
          return recarregar().catch(() => undefined);
        })
        .catch((e: unknown) => {
          setErro(mensagemDeEnvio(e));
          setCurrentStep(1);
        });
    },
    [recarregar],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const reset = () => {
    ultimoResultado = null;
    setResultado(null);
    setFile(null);
    setErro(null);
    setCurrentStep(1);
  };

  const atualizarAgora = () =>
    api
      .atualizarModelos()
      .then((r) => toast.success(r.message))
      .catch((e: unknown) => toast.error(mensagemDeEnvio(e)));

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
      {currentStep === 1 && !admin && (
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-8 flex items-start gap-4">
            <Lock size={22} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
            <div>
              <p className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                Só a gestora carrega planilhas
              </p>
              <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                Seu acesso é de consulta. Peça à gestora (perfil de administração) para enviar o relatório do mês.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {currentStep === 1 && admin && (
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-8 flex flex-col gap-4">
            {erro && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg px-4 py-3 text-sm"
                style={{ background: "rgba(212,24,61,0.08)", color: "var(--destructive)" }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                <span>
                  {file ? <strong>{file.name}: </strong> : null}
                  {erro}
                </span>
              </div>
            )}
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
                {[".xlsx", ".xlsm"].map((ext) => (
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
              accept=".xlsx,.xlsm"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
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
                  {file.size} · Lendo a planilha, conferindo vendas já carregadas e gravando as novas...
                </p>
              </div>
            </div>
            <Progress value={undefined} className="h-2 animate-pulse" />
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
              <Loader2 size={15} className="animate-spin" />
              Isso leva alguns segundos por mês de vendas.
            </div>
          </CardContent>
        </Card>
      )}

      {currentStep === 3 && resultado && (
        <Card className="border" style={{ borderColor: "var(--border)", background: "var(--secondary)" }}>
          <CardContent className="p-8 flex flex-col items-center gap-5">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{ background: "var(--primary)" }}
            >
              {resultado.rows_added > 0 ? <Sparkles size={28} color="#fff" /> : <CheckCircle2 size={28} color="#fff" />}
            </div>
            <div className="text-center">
              <p className="text-lg mb-1" style={{ color: "var(--foreground)", fontWeight: 700 }}>
                {resultado.rows_added > 0 ? "Planilha carregada!" : "Nenhuma venda nova nesta planilha"}
              </p>
              <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                {resultado.filename} · processada em {formatarNumero(resultado.processing_time_seconds)} s
              </p>
            </div>
            <div className="grid grid-cols-3 gap-4 w-full">
              {[
                { label: "Vendas novas gravadas", value: formatarNumero(resultado.rows_added) },
                { label: "Já estavam carregadas", value: formatarNumero(resultado.rows_duplicate) },
                { label: "Linhas ignoradas", value: formatarNumero(resultado.rows_skipped) },
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
            {resultado.errors.length > 0 && (
              <ul className="w-full text-xs flex flex-col gap-1" style={{ color: "#8a5a00" }}>
                {resultado.errors.map((e) => (
                  <li key={e} className="flex gap-2">
                    <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} /> {e}
                  </li>
                ))}
              </ul>
            )}
            {resultado.retrain_scheduled && (
              <p className="text-sm text-center" style={{ color: "var(--muted-foreground)" }}>
                A previsão passa a usar estas vendas na próxima atualização dos modelos
                {proximoTreino ? ` (${dataHora(proximoTreino)})` : ""}.
                Se preferir, atualize agora — leva cerca de 40 minutos.
              </p>
            )}
            <div className="flex gap-3 flex-wrap justify-center">
              <Button variant="outline" onClick={reset}>
                Enviar outro arquivo
              </Button>
              {admin && resultado.retrain_scheduled && (
                <Button variant="outline" onClick={atualizarAgora}>
                  Atualizar a previsão agora
                </Button>
              )}
              <Button style={{ background: "var(--primary)", color: "#fff" }} onClick={() => navigate("/pre-visualizacao")}>
                Conferir os dados →
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
                key={`${a.arquivo}-${a.hash}`}
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
