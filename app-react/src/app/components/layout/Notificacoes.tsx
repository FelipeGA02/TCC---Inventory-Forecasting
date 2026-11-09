import { useNavigate } from "react-router";
import { Bell, BrainCircuit, CheckCircle2, Database, Info, RefreshCw, XCircle, type LucideIcon } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Progress } from "../ui/progress";
import { AGENDA } from "@/config/agenda";
import { useDados } from "../../data/CarregarDados";
import type { StatusServicoPrevisao } from "../../data/api";
import { useServicoPrevisao } from "../../data/ServicoPrevisao";
import { formatarData, formatarNumero } from "@/lib/format";

type Tom = "alerta" | "andamento" | "sucesso" | "erro" | "info";

interface Notificacao {
  id: string;
  icone: LucideIcon;
  titulo: string;
  texto: string;
  tom?: Tom;
  acao?: { rotulo: string; destino: string };
  /** barra de andamento (0–100), para o treino em segundo plano */
  progresso?: number;
}

const UM_DIA = 86_400_000;
const CORES: Record<Tom, { cor: string; fundo: string; borda: string }> = {
  alerta: { cor: "#8a5a00", fundo: "#fff8e1", borda: "#ffe0a0" },
  andamento: { cor: "#1d4f91", fundo: "#eef4ff", borda: "#c9dbff" },
  info: { cor: "#1d4f91", fundo: "#eef4ff", borda: "#c9dbff" },
  sucesso: { cor: "#1a6b3c", fundo: "#ecf8f0", borda: "#bfe5cc" },
  erro: { cor: "#a12622", fundo: "#fdecea", borda: "#f5c2bf" },
};
/** Resultado de um treino do serviço de previsão fica no sino por um dia depois de terminar. */
const RESULTADO_TREINO_POR_MS = 86_400_000;

const dataCurta = (d: Date) => d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
const horaMinuto = (iso: string) => new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

/** Treino do serviço de previsão (só admin): andamento, ou o resultado do último por 1 dia. */
function notificacaoDoTreino(status: StatusServicoPrevisao | null, agora: Date): Notificacao | null {
  const andamento = status?.em_andamento;
  if (andamento) {
    const pct = Math.round(andamento.progresso_pct);
    const detalhe = andamento.total_series
      ? `${andamento.series_concluidas} de ${andamento.total_series} séries${andamento.serie_atual ? ` · ${andamento.serie_atual}` : ""}`
      : (andamento.mensagem ?? "Preparando o treino...");
    return {
      id: "treino",
      icone: BrainCircuit,
      tom: "andamento",
      titulo: `Treinando as previsões: ${pct}%`,
      texto: `${detalhe}. Você pode continuar usando o sistema.`,
      progresso: andamento.progresso_pct,
    };
  }
  const ultimo = status?.ultimo;
  if (!ultimo?.concluido_em || agora.getTime() - new Date(ultimo.concluido_em).getTime() > RESULTADO_TREINO_POR_MS) return null;
  const quandoTerminou = `${dataCurta(new Date(ultimo.concluido_em))} às ${horaMinuto(ultimo.concluido_em)}`;
  if (ultimo.status === "done") {
    return { id: "treino", icone: CheckCircle2, tom: "sucesso", titulo: `Previsões treinadas em ${quandoTerminou}`,
             texto: ultimo.mensagem ?? "Treino concluído.", acao: { rotulo: "Ver previsão", destino: "/previsao" } };
  }
  if (ultimo.status === "error") {
    return { id: "treino", icone: XCircle, tom: "erro", titulo: `O treino das previsões falhou (${quandoTerminou})`,
             texto: `${ultimo.mensagem ?? "Erro desconhecido."} Tente treinar de novo; se continuar, avise a equipe do projeto.` };
  }
  if (ultimo.status === "skipped") {
    return { id: "treino", icone: Info, tom: "info", titulo: `Treino não executado (${quandoTerminou})`,
             texto: ultimo.mensagem ?? "Os dados não mudaram desde o último treino." };
  }
  return null;
}

/**
 * O que pede ação — base desatualizada e vendas carregadas que a previsão ainda não usa — e,
 * para o admin, o andamento do treino das previsões (primeiro da lista).
 */
function useNotificacoes(): Notificacao[] {
  const { contexto } = useDados();
  const { status: servico } = useServicoPrevisao();
  const agora = new Date();
  const lista: Notificacao[] = [];
  const treino = notificacaoDoTreino(servico, agora);
  if (treino) lista.push(treino);
  if (!contexto?.base.fim) return lista;

  const ultimaVenda = new Date(`${contexto.base.fim}T23:59:59`);
  const diasSemVendas = Math.floor((agora.getTime() - ultimaVenda.getTime()) / UM_DIA);
  if (diasSemVendas > AGENDA.diasParaDesatualizado) {
    const diaSeguinte = new Date(ultimaVenda.getTime() + UM_DIA);
    lista.push({
      id: "dados",
      icone: Database,
      titulo: `Base sem vendas novas há ${formatarNumero(diasSemVendas)} dias`,
      texto: `Última venda carregada em ${formatarData(contexto.base.fim)}. Carregue as vendas a partir de ${diaSeguinte.toLocaleDateString("pt-BR")} e treine as previsões para elas usarem as vendas recentes.`,
      acao: { rotulo: "Carregar planilha", destino: "/importar" },
    });
  }

  // vendas carregadas depois do último treino: a previsão ainda não as usa
  const previsao = contexto.previsao;
  if (previsao && contexto.base.fim > previsao.dados_ate) {
    lista.push({
      id: "treinar",
      icone: RefreshCw,
      titulo: "Há vendas que a previsão ainda não usa",
      texto: `A previsão usa as vendas até ${formatarData(previsao.dados_ate)}; a base já tem vendas até ${formatarData(contexto.base.fim)}. A gestora atualiza com "Treinar previsões", no alto da tela.`,
    });
  }

  return lista;
}

export function Notificacoes() {
  const navigate = useNavigate();
  const notificacoes = useNotificacoes();
  const n = notificacoes.length;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="relative w-9 h-9 rounded-lg flex items-center justify-center hover:opacity-80 transition-colors"
          style={{ background: "var(--muted)" }}
          aria-label={n ? `${n} notificações` : "Sem notificações"}
        >
          <Bell size={16} style={{ color: "var(--muted-foreground)" }} />
          {n > 0 && (
            <span
              className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full text-[10px] flex items-center justify-center text-white"
              style={{ background: "var(--destructive)", fontWeight: 700 }}
            >
              {n}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0" onOpenAutoFocus={(e) => e.preventDefault()}>
        <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            Notificações
          </p>
        </div>
        <div className="p-3 flex flex-col gap-2">
          {n === 0 ? (
            <div className="flex items-center gap-2 text-xs px-1 py-2" style={{ color: "#1a6b3c" }}>
              <CheckCircle2 size={16} /> Nada pendente: base e previsão atualizadas.
            </div>
          ) : (
            notificacoes.map((a) => {
              const Icone = a.icone;
              const cor = CORES[a.tom ?? "alerta"];
              const acao = a.acao;
              return (
                <div key={a.id} className="rounded-lg px-3 py-2.5 flex items-start gap-2.5" style={{ background: cor.fundo, border: `1px solid ${cor.borda}` }}>
                  <Icone size={16} className="flex-shrink-0 mt-0.5" style={{ color: cor.cor }} aria-hidden />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs" style={{ fontWeight: 600, color: "var(--foreground)" }}>
                      {a.titulo}
                    </p>
                    {a.progresso !== undefined && (
                      <Progress value={a.progresso} className="h-1.5 mt-1.5" aria-label={`Andamento do treino: ${Math.round(a.progresso)}%`} />
                    )}
                    <p className="text-[11px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                      {a.texto}
                    </p>
                    {acao && (
                      <button className="text-[11px] mt-1.5 hover:underline" style={{ color: cor.cor, fontWeight: 600 }} onClick={() => navigate(acao.destino)}>
                        {acao.rotulo} →
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
        <div className="px-4 py-2.5 border-t flex items-start gap-2 text-[11px]" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
          <BrainCircuit size={13} className="flex-shrink-0 mt-0.5" />
          <span>
            A previsão não se atualiza sozinha: depois de carregar as planilhas, a gestora usa "Treinar previsões", no alto da
            tela. Cada treino prevê os próximos 3 meses a partir da última venda; a tela de previsão mostra 2 semanas, ou mais
            se você escolher.
          </span>
        </div>
      </PopoverContent>
    </Popover>
  );
}
