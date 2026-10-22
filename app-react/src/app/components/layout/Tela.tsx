/**
 * Área de uma tela: busca os dados de que ela precisa (`recursos`) ao abrir e, enquanto
 * isso, mostra a espera só no lugar do conteúdo — o menu lateral e o cabeçalho continuam.
 * A tela em si (`children`, carregada sob demanda com `lazy`) só é montada depois dos dados.
 */
import { Component, Suspense, useEffect, useState, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { ApiError, mensagemDoErro } from "@/lib/http/errors";
import { useAuth } from "../../auth/AuthContext";
import { api } from "../../data/api";
import { useDados } from "../../data/CarregarDados";
import { estaoProntos, garantir, type Recurso } from "../../data/recursos";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";

export function CarregandoTela({ mensagem }: { mensagem: string }) {
  return (
    <div className="h-full min-h-[60vh] flex flex-col items-center justify-center gap-3" role="status" aria-live="polite">
      <Loader2 size={28} className="animate-spin" style={{ color: "var(--primary)" }} />
      <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
        {mensagem}
      </p>
    </div>
  );
}

export function ErroTela({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  const { usuario } = useAuth();
  const treinoNaApi = useDados().contexto?.configuracao.treino_na_api !== false;
  const [aviso, setAviso] = useState<string | null>(null);
  const atualizarModelos = () => {
    setAviso(null);
    api
      .atualizarModelos()
      .then((r) => setAviso(r.message))
      .catch((e: unknown) => setAviso(mensagemDoErro(e)));
  };
  return (
    <div className="h-full min-h-[60vh] flex items-center justify-center p-6">
      <Card className="border w-full max-w-md" style={{ borderColor: "var(--border)" }}>
        <CardContent className="p-6 flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={22} style={{ color: "var(--chart-4)", flexShrink: 0 }} />
            <div>
              <p className="text-sm" style={{ fontWeight: 600, color: "var(--foreground)" }}>
                Não foi possível abrir esta tela
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
                {mensagem}
              </p>
              {aviso && (
                <p className="text-sm mt-2" style={{ color: "var(--primary)" }}>
                  {aviso}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 justify-end">
            {usuario?.perfil === "admin" && treinoNaApi && (
              <Button variant="outline" onClick={atualizarModelos}>
                Atualizar os modelos
              </Button>
            )}
            <Button className="gap-2" style={{ background: "var(--primary)", color: "#fff" }} onClick={onTentar}>
              <RefreshCw size={14} /> Tentar de novo
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function mensagemDeCarga(erro: unknown): string {
  // 409: ainda não há previsão gravada — a API explica o que fazer.
  if (erro instanceof ApiError && erro.status === 409 && erro.detail) return erro.detail;
  return mensagemDoErro(erro);
}

/**
 * Um erro ao desenhar a tela fica só na área dela (com "Tentar de novo"); sem isso o React
 * desmonta o app inteiro e sobra a página em branco.
 */
class BarreiraDeErro extends Component<{ children: ReactNode }, { erro: Error | null }> {
  state = { erro: null as Error | null };

  static getDerivedStateFromError(erro: Error) {
    return { erro };
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error("[tela]", erro, info.componentStack);
  }

  render() {
    if (this.state.erro) {
      return (
        <ErroTela
          mensagem="Algo deu errado ao montar esta tela. Tente de novo; se continuar, atualize a página."
          onTentar={() => this.setState({ erro: null })}
        />
      );
    }
    return this.props.children;
  }
}

/** Use com `key` diferente em cada rota: o estado de uma tela não pode passar para a outra. */
export function Tela({ recursos = [], mensagem, children }: { recursos?: Recurso[]; mensagem: string; children: ReactNode }) {
  const [, setPronto] = useState(() => estaoProntos(recursos));
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const chave = recursos.join(",");

  useEffect(() => {
    if (estaoProntos(recursos)) {
      setPronto(true);
      return;
    }
    let vivo = true;
    setPronto(false);
    setErro(null);
    garantir(recursos)
      .then(() => vivo && setPronto(true))
      .catch((e: unknown) => vivo && setErro(mensagemDeCarga(e)));
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, tentativa]);

  if (erro) return <ErroTela mensagem={erro} onTentar={() => setTentativa((t) => t + 1)} />;
  // conferido no próprio render (não só no estado): a tela nunca é desenhada sem os dados
  if (!estaoProntos(recursos)) return <CarregandoTela mensagem={mensagem} />;
  return (
    <BarreiraDeErro>
      <Suspense fallback={<CarregandoTela mensagem="Abrindo a tela..." />}>{children}</Suspense>
    </BarreiraDeErro>
  );
}
