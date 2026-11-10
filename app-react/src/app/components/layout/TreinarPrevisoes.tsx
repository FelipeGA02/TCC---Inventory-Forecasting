/**
 * Botão "Treinar previsões" (só admin) e o modal de confirmação.
 *
 * Ao abrir, o modal confere com a API se há dados novos desde o último treino: sem dados
 * novos o treino não roda (a API registra o disparo como pulado), então o botão de
 * confirmar fica desabilitado e o modal explica por quê. O treino roda em segundo plano e o
 * andamento aparece no sino de notificações.
 */
import { useState, type ReactNode } from "react";
import { BrainCircuit, CheckCircle2, Info, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError, mensagemDoErro } from "@/lib/http/errors";
import { useServicoPrevisao } from "../../data/ServicoPrevisao";
import { Button } from "../ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

function Aviso({ tom, children }: { tom: "info" | "ok" | "espera"; children: ReactNode }) {
  const cores = {
    info: { cor: "#1d4f91", fundo: "#eef4ff", borda: "#c9dbff", Icone: Info },
    ok: { cor: "#1a6b3c", fundo: "#ecf8f0", borda: "#bfe5cc", Icone: CheckCircle2 },
    espera: { cor: "var(--muted-foreground)", fundo: "var(--muted)", borda: "var(--border)", Icone: Loader2 },
  }[tom];
  return (
    <div className="rounded-lg px-3 py-2.5 flex items-start gap-2 text-xs" style={{ background: cores.fundo, border: `1px solid ${cores.borda}`, color: cores.cor }}>
      <cores.Icone size={15} className={`flex-shrink-0 mt-0.5 ${tom === "espera" ? "animate-spin" : ""}`} aria-hidden />
      <span>{children}</span>
    </div>
  );
}

export function TreinarPrevisoes() {
  const { disponivel, status, atualizar, disparar } = useServicoPrevisao();
  const [aberto, setAberto] = useState(false);
  const [conferindo, setConferindo] = useState(false);
  const [enviando, setEnviando] = useState(false);

  if (!disponivel || status?.treino_na_api === false) return null;

  const andamento = status?.em_andamento ?? null;
  const semDadosNovos = status?.dados_alterados === false;
  const podeTreinar = Boolean(status) && !conferindo && !andamento && !semDadosNovos && !enviando;
  const horizonte = status?.config.horizonte_dias ?? 14;
  const diasPrevistos = status?.config.horizonte_previsao_dias ?? horizonte;
  const semanas = Math.round((status?.config.origens ?? 56) / 7);

  const abrir = async () => {
    setAberto(true);
    setConferindo(true);
    await atualizar(); // confere os dados na hora de decidir, não na última consulta de fundo
    setConferindo(false);
  };

  const confirmar = async () => {
    setEnviando(true);
    try {
      const r = await disparar();
      if (r.iniciado) toast.success("Treino iniciado. Acompanhe o andamento no sino de notificações.");
      else toast.info(r.mensagem);
      setAberto(false);
    } catch (e) {
      // 409 (já em andamento) e 503 (esta instalação não treina) trazem a explicação da API
      toast.error(e instanceof ApiError && e.detail ? e.detail : mensagemDoErro(e));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="gap-2 text-xs"
        style={{ color: "var(--muted-foreground)" }}
        onClick={() => void abrir()}
        disabled={Boolean(andamento)}
        title={andamento ? "Treino em andamento: acompanhe no sino de notificações" : "Treinar as previsões das categorias e dos produtos de grama"}
      >
        {andamento ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
        {andamento ? `Treinando... ${Math.round(andamento.progresso_pct)}%` : "Treinar previsões"}
      </Button>

      <AlertDialog open={aberto} onOpenChange={(v) => !enviando && setAberto(v)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Treinar as previsões?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="flex flex-col gap-3 text-sm" style={{ color: "var(--muted-foreground)" }}>
                <p>
                  Calcula a previsão de vendas dos próximos {diasPrevistos} dias de cada uma das 4 categorias e de cada produto
                  de grama, nas 2 lojas. Antes de gravar, testa o acerto da previsão das 2 primeiras semanas ({horizonte} dias),
                  dia a dia, nas últimas {semanas} semanas. Usa as vendas do balcão, sem as encomendas grandes.
                </p>
                <p>Roda em segundo plano: você pode continuar usando o sistema e acompanhar o andamento no sino de notificações.</p>
                {conferindo || !status ? (
                  <Aviso tom="espera">Conferindo se há dados novos desde o último treino...</Aviso>
                ) : andamento ? (
                  <Aviso tom="info">Já existe um treino em andamento ({Math.round(andamento.progresso_pct)}%). Espere ele terminar.</Aviso>
                ) : semDadosNovos ? (
                  <Aviso tom="info">
                    Os dados não mudaram desde o último treino
                    {status.ultimo_concluido_em ? `, em ${dataHora(status.ultimo_concluido_em)}` : ""}. Não há o que treinar:
                    carregue planilhas novas e tente de novo.
                  </Aviso>
                ) : status.ultimo_concluido_em ? (
                  <Aviso tom="ok">Há dados novos desde o último treino, em {dataHora(status.ultimo_concluido_em)}.</Aviso>
                ) : (
                  <Aviso tom="ok">Ainda não há treino concluído: este será o primeiro.</Aviso>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={enviando}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={!podeTreinar}
              onClick={(e) => {
                e.preventDefault(); // o modal só fecha quando a API responde
                void confirmar();
              }}
              style={{ background: "var(--primary)", color: "#fff" }}
            >
              {enviando ? "Iniciando..." : "Treinar agora"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
