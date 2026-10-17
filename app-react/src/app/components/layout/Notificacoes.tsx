import { useNavigate } from "react-router";
import { AlertTriangle, Bell, CalendarClock, CheckCircle2, Database, type LucideIcon } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { AGENDA, proximoDiaSemana } from "@/config/agenda";
import { dados, produtosDe, unidadesDoFiltro } from "../../data/mockData";
import { useFiltroLoja } from "../shared";
import { formatarData, formatarNumero } from "@/lib/format";

interface Notificacao {
  id: string;
  icone: LucideIcon;
  titulo: string;
  texto: string;
  acao: { rotulo: string; destino: string };
}

const DIAS_SEMANA = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
const UM_DIA = 86_400_000;
const COR = { cor: "#8a5a00", fundo: "#fff8e1", borda: "#ffe0a0" };

function quando(alvo: Date, agora: Date): string {
  const dias = Math.round((new Date(alvo).setHours(0, 0, 0, 0) - new Date(agora).setHours(0, 0, 0, 0)) / UM_DIA);
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  return `em ${dias} dias`;
}

const hora = (d: Date) => `${String(d.getHours()).padStart(2, "0")}:00`;
const dataCurta = (d: Date) => d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });

/** Só o que pede ação: base desatualizada e previsões que não passaram nos testes. */
function useNotificacoes(): Notificacao[] {
  const { unidade } = useFiltroLoja();
  const agora = new Date();
  const lista: Notificacao[] = [];

  const ultimaVenda = new Date(`${dados.base.fim}T23:59:59`);
  const diasSemVendas = Math.floor((agora.getTime() - ultimaVenda.getTime()) / UM_DIA);
  if (diasSemVendas > AGENDA.diasParaDesatualizado) {
    const mesSeguinte = new Date(ultimaVenda.getFullYear(), ultimaVenda.getMonth() + 1, 1);
    lista.push({
      id: "dados",
      icone: Database,
      titulo: `Base sem vendas novas há ${formatarNumero(diasSemVendas)} dias`,
      texto: `Última venda carregada em ${formatarData(dados.base.fim)}. Carregue as planilhas a partir de ${mesSeguinte.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })} para a previsão usar as vendas recentes.`,
      acao: { rotulo: "Carregar planilha", destino: "/importar" },
    });
  }

  const regulares = produtosDe(unidade, "todas", true);
  const cautela = regulares.filter((p) => p.modelo?.status === "low_confidence");
  const lojasCautela = unidadesDoFiltro(unidade).filter((u) => u.modelo.status !== "trained");
  if (lojasCautela.length || cautela.length) {
    const partes = [
      lojasCautela.length ? `loja ${lojasCautela.map((u) => u.nome).join(" e ")}` : "",
      cautela.length ? `${cautela.length} de ${regulares.length} produtos com previsão própria` : "",
    ].filter(Boolean);
    lista.push({
      id: "confianca",
      icone: AlertTriangle,
      titulo: `Previsão para usar com cautela: ${partes.join(" · ")}`,
      texto: `Não passaram em todos os testes de acerto${cautela.length ? ` (ex.: ${cautela.slice(0, 3).map((p) => p.nome).join(", ")})` : ""}. Confira a faixa antes de decidir.`,
      acao: { rotulo: "Ver previsão", destino: "/previsao" },
    });
  }
  return lista;
}

export function Notificacoes() {
  const navigate = useNavigate();
  const notificacoes = useNotificacoes();
  const agora = new Date();
  const treino = proximoDiaSemana(agora, AGENDA.treinoDiaSemana, AGENDA.treinoHora);
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
              <CheckCircle2 size={16} /> Nada pendente: base atualizada e previsões confiáveis.
            </div>
          ) : (
            notificacoes.map((a) => {
              const Icone = a.icone;
              return (
                <div key={a.id} className="rounded-lg px-3 py-2.5 flex items-start gap-2.5" style={{ background: COR.fundo, border: `1px solid ${COR.borda}` }}>
                  <Icone size={16} className="flex-shrink-0 mt-0.5" style={{ color: COR.cor }} aria-hidden />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs" style={{ fontWeight: 600, color: "var(--foreground)" }}>
                      {a.titulo}
                    </p>
                    <p className="text-[11px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                      {a.texto}
                    </p>
                    <button className="text-[11px] mt-1.5 hover:underline" style={{ color: COR.cor, fontWeight: 600 }} onClick={() => navigate(a.acao.destino)}>
                      {a.acao.rotulo} →
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
        <div className="px-4 py-2.5 border-t flex items-start gap-2 text-[11px]" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
          <CalendarClock size={13} className="flex-shrink-0 mt-0.5" />
          <span>
            Próximo treino dos modelos: {DIAS_SEMANA[treino.getDay()]}, {dataCurta(treino)} às {hora(treino)} ({quando(treino, agora)}), se
            houver vendas novas. A previsão é atualizada logo depois de cada treino.
          </span>
        </div>
      </PopoverContent>
    </Popover>
  );
}
