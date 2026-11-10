import { useEffect, useState, type ReactNode } from "react";
import { BarChart3, Database, Download, FileSpreadsheet, FileText, LineChart, Loader2, Printer, RefreshCw, ShieldCheck, Upload } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import type { FiltroUnidade } from "@/domain/types";
import { nomeUnidade, textoHorizonte } from "../../data/painel";
import {
  documentoImpressao,
  formatarCelula,
  horizonteDe,
  relatorioGerencial,
  relatorioGerencialHtml,
  relatorios,
  type FiltrosRelatorio,
  type Formato,
  type GrupoRelatorio,
  type Relatorio,
} from "../../data/relatorios";
import { api, type Atividade } from "../../data/api";
import { mensagemDoErro } from "@/lib/http/errors";
import { baixarCsv, baixarXlsx, imprimirHtml, tabelaHtml } from "@/lib/exportar";
import { formatarData, formatarNumero } from "@/lib/format";
import { Segmentado, opcoesLoja, useFiltroLoja } from "../shared";

/**
 * Relatórios: a lista de relatórios para baixar, com um só filtro (a loja), e o log de uso do
 * sistema — as planilhas enviadas e os treinos da previsão (`GET /api/v1/atividades`).
 *
 * Os relatórios saem com todas as categorias e, os de previsão, com o horizonte escolhido na
 * tela Previsão de Vendas (padrão 2 semanas, ADR-021).
 */

const GRUPOS: { grupo: GrupoRelatorio; icone: typeof LineChart }[] = [
  { grupo: "Previsão", icone: LineChart },
  { grupo: "Histórico de vendas", icone: BarChart3 },
  { grupo: "Qualidade da previsão", icone: ShieldCheck },
  { grupo: "Base de dados", icone: Database },
];

const ROTULO_FORMATO: Record<Formato, string> = { xlsx: "Excel", csv: "CSV", pdf: "PDF" };
const POR_PAGINA_LOG = 20;

const slug = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

const avisoPopup = () =>
  toast.error("O navegador bloqueou a janela de impressão.", { description: "Permita pop-ups para este site e tente de novo." });

// ---------------------------------------------------------------------------
// Log de uso
// ---------------------------------------------------------------------------

const SITUACAO: Record<Atividade["situacao"], { label: string; cor: string; fundo: string }> = {
  concluido: { label: "Concluído", cor: "#1a6b3c", fundo: "#e8f5e0" },
  sem_dados_novos: { label: "Sem dados novos", cor: "#5a6570", fundo: "#f1f3f5" },
  em_andamento: { label: "Em andamento", cor: "#8a5a00", fundo: "#fff4d6" },
  erro: { label: "Erro", cor: "#b4232a", fundo: "#fdecec" },
};

function evento(a: Atividade): string {
  if (a.tipo === "treino") return "Treino da previsão";
  return a.origem === "carga_inicial" ? "Carga inicial da base" : "Planilha enviada";
}

function detalhe(a: Atividade): string {
  if (a.situacao === "erro") return a.mensagem ?? "Não foi concluído.";
  if (a.tipo === "treino") {
    if (a.situacao === "sem_dados_novos") return "Nenhuma venda nova desde o último treino: a previsão continuou a mesma.";
    if (a.situacao === "em_andamento") return "Treinando…";
    return [
      a.dados_ate ? `vendas até ${formatarData(a.dados_ate)}` : "",
      `${formatarNumero(a.series_com_previsao ?? 0)} previsões geradas`,
      a.series_sem_dados ? `${formatarNumero(a.series_sem_dados)} itens com pouca venda` : "",
      a.series_com_falha ? `${formatarNumero(a.series_com_falha)} com falha` : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  return [
    a.arquivo ?? "",
    a.periodo ? `${formatarData(a.periodo[0])} a ${formatarData(a.periodo[1])}` : "",
    a.linhas_novas !== null ? `${formatarNumero(a.linhas_novas)} linhas novas` : "",
    a.linhas_duplicadas ? `${formatarNumero(a.linhas_duplicadas)} já carregadas` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function quem(a: Atividade): string {
  if (a.usuario) return a.usuario;
  if (a.origem === "script") return "Servidor (script)";
  if (a.origem === "carga_inicial") return "Instalação do sistema";
  return "—";
}

function LogDeUso() {
  const [itens, setItens] = useState<Atividade[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrar, setMostrar] = useState(POR_PAGINA_LOG);
  const [carregando, setCarregando] = useState(false);

  const carregar = () => {
    setCarregando(true);
    setErro(null);
    api
      .atividades()
      .then(setItens)
      .catch((e: unknown) => setErro(mensagemDoErro(e)))
      .finally(() => setCarregando(false));
  };
  useEffect(carregar, []);

  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardHeader className="pb-3 pt-5 px-5 flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Uso do sistema
          </CardTitle>
          <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
            Planilhas enviadas e treinos da previsão, do mais recente para o mais antigo.
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5 text-xs h-8" onClick={carregar} disabled={carregando}>
          <RefreshCw size={13} className={carregando ? "animate-spin" : ""} /> Atualizar
        </Button>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {erro ? (
          <p className="text-xs px-5 pb-5" style={{ color: "var(--destructive)" }}>
            {erro}
          </p>
        ) : itens === null ? (
          <p className="text-xs px-5 pb-5 flex items-center gap-2" style={{ color: "var(--muted-foreground)" }}>
            <Loader2 size={13} className="animate-spin" /> Carregando...
          </p>
        ) : itens.length === 0 ? (
          <p className="text-xs px-5 pb-5" style={{ color: "var(--muted-foreground)" }}>
            Nenhuma planilha enviada nem treino feito ainda.
          </p>
        ) : (
          <>
            <ul className="border-t divide-y" style={{ borderColor: "var(--border)" }}>
              {itens.slice(0, mostrar).map((a) => {
                const s = SITUACAO[a.situacao];
                const Icone = a.tipo === "treino" ? LineChart : Upload;
                return (
                  <li key={`${a.tipo}-${a.id}`} className="px-5 py-3 flex items-start gap-3" style={{ borderColor: "var(--border)" }}>
                    <span className="mt-0.5 w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "var(--secondary)" }}>
                      <Icone size={14} style={{ color: "var(--primary)" }} />
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs flex items-center gap-2 flex-wrap" style={{ fontWeight: 600 }}>
                        {evento(a)}
                        <span className="rounded-full px-2 py-0.5 text-[10px]" style={{ background: s.fundo, color: s.cor, fontWeight: 600 }}>
                          {s.label}
                        </span>
                      </p>
                      <p className="text-xs mt-0.5 break-words" style={{ color: a.situacao === "erro" ? "var(--destructive)" : "var(--muted-foreground)" }}>
                        {detalhe(a)}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs whitespace-nowrap">{dataHora(a.inicio)}</p>
                      <p className="text-[11px] whitespace-nowrap" style={{ color: "var(--muted-foreground)" }}>
                        {quem(a)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
            {itens.length > mostrar && (
              <div className="border-t px-5 py-3 text-center" style={{ borderColor: "var(--border)" }}>
                <Button variant="ghost" size="sm" className="text-xs" onClick={() => setMostrar((m) => m + POR_PAGINA_LOG)}>
                  Mostrar mais ({formatarNumero(itens.length - mostrar)})
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Tela
// ---------------------------------------------------------------------------

function BotaoFormato({ formato, onClick }: { formato: Formato; onClick: () => void }) {
  return (
    <Button variant="outline" size="sm" className="gap-1.5 text-xs h-8" onClick={onClick}>
      {formato === "pdf" ? <Printer size={13} /> : formato === "xlsx" ? <FileSpreadsheet size={13} /> : <Download size={13} />}
      {ROTULO_FORMATO[formato]}
    </Button>
  );
}

function Linha({ titulo, uso, children }: { titulo: string; uso: string; children: ReactNode }) {
  return (
    <li className="px-5 py-3 flex items-center gap-4 flex-wrap" style={{ borderColor: "var(--border)" }}>
      <div className="flex-1 min-w-[220px]">
        <p className="text-xs" style={{ fontWeight: 600 }}>
          {titulo}
        </p>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
          {uso}
        </p>
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </li>
  );
}

export function ExportarRelatorios() {
  const { unidade: unidadeGlobal, horizonte } = useFiltroLoja();
  const [unidade, setUnidade] = useState<FiltroUnidade>(unidadeGlobal);
  const filtros: FiltrosRelatorio = { unidade, categoria: "todas", horizonte };

  const baixar = (r: Relatorio, formato: Formato) => {
    const t = r.gerar(filtros);
    const nome = slug(`${r.titulo}-${nomeUnidade(unidade)}`);
    if (formato === "csv") baixarCsv(t, nome);
    else if (formato === "xlsx") baixarXlsx(t, nome, r.titulo);
    else if (!imprimirHtml(documentoImpressao(r.titulo, `${nomeUnidade(unidade)} · ${r.descricao}`, tabelaHtml(t, formatarCelula)))) {
      avisoPopup();
      return;
    }
    toast.success(formato === "pdf" ? "Relatório aberto para impressão" : "Download iniciado", {
      description: formato === "pdf" ? "Escolha “Salvar como PDF” na janela de impressão." : `${r.titulo} · ${formatarNumero(t.linhas.length)} linhas`,
    });
  };

  const gerarGerencial = () => {
    if (!imprimirHtml(relatorioGerencialHtml(filtros))) return avisoPopup();
    toast.success("Relatório gerencial aberto", { description: "Escolha “Salvar como PDF” na janela de impressão." });
  };

  return (
    <div className="p-6 flex flex-col gap-5 max-w-5xl">
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-5 px-5 flex flex-row items-start justify-between gap-4 flex-wrap">
          <div>
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Relatórios
            </CardTitle>
            <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
              Todas as categorias. Previsões das próximas {textoHorizonte(horizonteDe(filtros))}, o horizonte escolhido na tela Previsão de Vendas.
            </p>
          </div>
          <Segmentado rotulo="Loja" opcoes={opcoesLoja()} valor={unidade} onChange={setUnidade} />
        </CardHeader>
        <CardContent className="px-0 pb-1">
          {GRUPOS.map(({ grupo, icone: Icone }) => (
            <section key={grupo}>
              <p className="px-5 pt-3 pb-1 text-[11px] uppercase tracking-wide flex items-center gap-1.5 border-t" style={{ color: "var(--muted-foreground)", fontWeight: 600, borderColor: "var(--border)" }}>
                <Icone size={12} /> {grupo}
              </p>
              <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
                {grupo === "Previsão" && (
                  <Linha titulo={relatorioGerencial.titulo} uso={relatorioGerencial.uso}>
                    <Button size="sm" className="gap-1.5 text-xs h-8" style={{ background: "var(--primary)", color: "#fff" }} onClick={gerarGerencial}>
                      <FileText size={13} /> PDF
                    </Button>
                  </Linha>
                )}
                {relatorios
                  .filter((r) => r.grupo === grupo)
                  .map((r) => (
                    <Linha key={r.id} titulo={r.titulo} uso={r.uso}>
                      {r.formatos
                        .filter((f) => f !== "csv")
                        .map((f) => (
                          <BotaoFormato key={f} formato={f} onClick={() => baixar(r, f)} />
                        ))}
                    </Linha>
                  ))}
              </ul>
            </section>
          ))}
        </CardContent>
      </Card>

      <LogDeUso />
    </div>
  );
}
