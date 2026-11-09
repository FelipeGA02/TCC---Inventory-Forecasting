import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Clock,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  History,
  LineChart,
  Printer,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import type { FiltroUnidade } from "@/domain/types";
import { categorias, nomeCategoria, nomeUnidade } from "../../data/painel";
import {
  documentoImpressao,
  formatarCelula,
  relatorioGerencial,
  horizonteDe,
  relatorioGerencialHtml,
  relatorios,
  type FiltroCategoria,
  type FiltrosRelatorio,
  type Formato,
  type GrupoRelatorio,
  type Relatorio,
} from "../../data/relatorios";
import { baixarCsv, baixarXlsx, imprimirHtml, tabelaHtml } from "@/lib/exportar";
import { formatarNumero, formatarTamanhoArquivo } from "@/lib/format";
import { FiltroHorizonte, Segmentado, opcoesLoja, useFiltroLoja } from "../shared";

const LINHAS_PREVIA = 12;
const CHAVE_HISTORICO = "verde-perto:relatorios-baixados";

const ICONE_GRUPO: Record<GrupoRelatorio, typeof LineChart> = {
  Previsão: LineChart,
  "Histórico de vendas": BarChart3,
  "Qualidade da previsão": ShieldCheck,
  "Base de dados": Database,
};

const ROTULO_FORMATO: Record<Formato, string> = { xlsx: "Excel", csv: "CSV", pdf: "PDF" };

interface Baixado {
  id: number;
  relatorioId: string;
  titulo: string;
  formato: Formato;
  filtros: FiltrosRelatorio;
  quando: string;
  tamanho: number | null;
}

function lerHistorico(): Baixado[] {
  try {
    const bruto = localStorage.getItem(CHAVE_HISTORICO);
    return bruto ? (JSON.parse(bruto) as Baixado[]) : [];
  } catch {
    return [];
  }
}

function gravarHistorico(lista: Baixado[]): void {
  try {
    localStorage.setItem(CHAVE_HISTORICO, JSON.stringify(lista.slice(0, 15)));
  } catch {
    /* armazenamento indisponível: o histórico fica só nesta visita */
  }
}

const slug = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

function descreverFiltros(r: { filtros?: Relatorio["filtros"] }, f: FiltrosRelatorio): string {
  const partes: string[] = [];
  if (!r.filtros || r.filtros.includes("unidade")) partes.push(nomeUnidade(f.unidade));
  if (r.filtros?.includes("categoria")) partes.push(f.categoria === "todas" ? "todas as categorias" : nomeCategoria(f.categoria));
  if (!r.filtros || r.filtros.includes("horizonte")) partes.push(`próximos ${horizonteDe(f)} dias`);
  return partes.join(" · ");
}

const opcoesCategoria: { valor: FiltroCategoria; label: string }[] = [
  { valor: "todas", label: "Todas" },
  ...categorias.map((c) => ({ valor: c.id as FiltroCategoria, label: c.nome })),
];

export function ExportarRelatorios() {
  const { unidade: unidadeGlobal, categoria: categoriaGlobal, horizonte: horizonteGlobal } = useFiltroLoja();
  const [selecionado, setSelecionado] = useState<string>(relatorios[0]!.id);
  const [filtros, setFiltros] = useState<FiltrosRelatorio>({ unidade: unidadeGlobal, categoria: categoriaGlobal, horizonte: horizonteGlobal });
  const [lojaGerencial, setLojaGerencial] = useState<FiltroUnidade>(unidadeGlobal);
  const [horizonteGerencial, setHorizonteGerencial] = useState<number>(horizonteGlobal);
  const [historico, setHistorico] = useState<Baixado[]>(lerHistorico);

  useEffect(() => gravarHistorico(historico), [historico]);

  const relatorio = relatorios.find((r) => r.id === selecionado)!;
  const tabela = useMemo(() => relatorio.gerar(filtros), [relatorio, filtros]);

  const grupos = useMemo(() => {
    const m = new Map<GrupoRelatorio, Relatorio[]>();
    for (const r of relatorios) m.set(r.grupo, [...(m.get(r.grupo) ?? []), r]);
    return [...m.entries()];
  }, []);

  const registrar = (relatorioId: string, titulo: string, formato: Formato, f: FiltrosRelatorio, tamanho: number | null) => {
    setHistorico((h) => [{ id: Date.now(), relatorioId, titulo, formato, filtros: f, quando: new Date().toISOString(), tamanho }, ...h]);
  };

  const baixar = (r: Relatorio, formato: Formato, f: FiltrosRelatorio) => {
    const t = r.gerar(f);
    const nome = slug(`${r.titulo}-${descreverFiltros(r, f)}`);
    let tamanho: number | null = null;
    if (formato === "csv") tamanho = baixarCsv(t, nome);
    else if (formato === "xlsx") tamanho = baixarXlsx(t, nome, r.titulo);
    else {
      const ok = imprimirHtml(documentoImpressao(r.titulo, `${descreverFiltros(r, f)} · ${r.descricao}`, tabelaHtml(t, formatarCelula)));
      if (!ok) {
        toast.error("O navegador bloqueou a janela de impressão.", { description: "Permita pop-ups para este site e tente de novo." });
        return;
      }
    }
    registrar(r.id, r.titulo, formato, f, tamanho);
    toast.success(formato === "pdf" ? "Relatório aberto para impressão" : "Download iniciado", {
      description: formato === "pdf" ? "Escolha “Salvar como PDF” na janela de impressão." : `${r.titulo} · ${formatarNumero(t.linhas.length)} linhas`,
    });
  };

  const gerarGerencial = () => {
    const f: FiltrosRelatorio = { unidade: lojaGerencial, categoria: "todas", horizonte: horizonteGerencial };
    if (!imprimirHtml(relatorioGerencialHtml(f))) {
      toast.error("O navegador bloqueou a janela de impressão.", { description: "Permita pop-ups para este site e tente de novo." });
      return;
    }
    registrar(relatorioGerencial.id, relatorioGerencial.titulo, "pdf", f, null);
    toast.success("Relatório gerencial aberto", { description: "Escolha “Salvar como PDF” na janela de impressão." });
  };

  const rebaixar = (b: Baixado) => {
    if (b.relatorioId === relatorioGerencial.id) {
      setLojaGerencial(b.filtros.unidade);
      setHorizonteGerencial(horizonteDe(b.filtros));
      if (imprimirHtml(relatorioGerencialHtml(b.filtros))) registrar(b.relatorioId, b.titulo, "pdf", b.filtros, null);
      return;
    }
    const r = relatorios.find((x) => x.id === b.relatorioId);
    if (r) baixar(r, b.formato, b.filtros);
  };

  return (
    <div className="p-6 flex flex-col gap-5">
      {/* Destaque: relatório gerencial */}
      <Card className="border" style={{ borderColor: "var(--border)", background: "linear-gradient(90deg, #e8f5e0 0%, #ffffff 70%)" }}>
        <CardContent className="p-5 flex items-center gap-5 flex-wrap">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "var(--primary)" }}>
            <FileText size={22} color="#fff" />
          </div>
          <div className="flex-1 min-w-[260px]">
            <p className="text-sm" style={{ fontWeight: 600 }}>
              {relatorioGerencial.titulo} <span className="text-xs ml-1 px-1.5 py-0.5 rounded" style={{ background: "#fff", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>PDF</span>
            </p>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              {relatorioGerencial.descricao}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <Segmentado rotulo="Loja" opcoes={opcoesLoja()} valor={lojaGerencial} onChange={setLojaGerencial} />
            <FiltroHorizonte valor={horizonteGerencial} onChange={setHorizonteGerencial} />
            <Button className="gap-1.5 text-xs" style={{ background: "var(--primary)", color: "#fff" }} onClick={gerarGerencial}>
              <Printer size={14} /> Gerar PDF
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[300px_1fr] gap-5 items-start">
        {/* Catálogo */}
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Relatórios disponíveis
            </CardTitle>
          </CardHeader>
          <CardContent className="px-2 pb-3 flex flex-col gap-3">
            {grupos.map(([grupo, lista]) => {
              const Icone = ICONE_GRUPO[grupo];
              return (
                <div key={grupo} className="flex flex-col gap-0.5">
                  <p className="px-2 py-1 text-[11px] uppercase tracking-wide flex items-center gap-1.5" style={{ color: "var(--muted-foreground)", fontWeight: 600 }}>
                    <Icone size={12} /> {grupo}
                  </p>
                  {lista.map((r) => {
                    const ativo = r.id === selecionado;
                    return (
                      <button
                        key={r.id}
                        onClick={() => setSelecionado(r.id)}
                        className="text-left px-3 py-2 rounded-lg transition-colors"
                        style={{
                          background: ativo ? "var(--secondary)" : "transparent",
                          borderLeft: `3px solid ${ativo ? "var(--primary)" : "transparent"}`,
                        }}
                      >
                        <p className="text-xs" style={{ fontWeight: ativo ? 600 : 500, color: ativo ? "var(--primary)" : "var(--foreground)" }}>
                          {r.titulo}
                        </p>
                        <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                          {r.formatos.map((f) => ROTULO_FORMATO[f]).join(" · ")}
                        </p>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Pré-visualização */}
        <div className="flex flex-col gap-5 min-w-0">
          <Card className="border" style={{ borderColor: "var(--border)" }}>
            <CardHeader className="pb-3 pt-5 px-5 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <CardTitle className="text-base" style={{ fontWeight: 600 }}>
                    {relatorio.titulo}
                  </CardTitle>
                  <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                    {relatorio.descricao}
                  </p>
                  <p className="text-xs mt-1" style={{ color: "var(--secondary-foreground)" }}>
                    <strong>Para que serve:</strong> {relatorio.uso}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {relatorio.formatos.map((f) => (
                    <Button
                      key={f}
                      size="sm"
                      variant={f === relatorio.formatos[0] ? "default" : "outline"}
                      className="gap-1.5 text-xs"
                      style={f === relatorio.formatos[0] ? { background: "var(--primary)", color: "#fff" } : undefined}
                      onClick={() => baixar(relatorio, f, filtros)}
                    >
                      {f === "pdf" ? <Printer size={13} /> : f === "xlsx" ? <FileSpreadsheet size={13} /> : <Download size={13} />}
                      {f === "pdf" ? "Imprimir / PDF" : `Baixar ${ROTULO_FORMATO[f]}`}
                    </Button>
                  ))}
                </div>
              </div>

              {relatorio.filtros.length > 0 && (
                <div className="flex items-center gap-5 flex-wrap pt-3 border-t" style={{ borderColor: "var(--border)" }}>
                  {relatorio.filtros.includes("unidade") && (
                    <Segmentado rotulo="Loja" opcoes={opcoesLoja()} valor={filtros.unidade} onChange={(unidade) => setFiltros((f) => ({ ...f, unidade }))} />
                  )}
                  {relatorio.filtros.includes("categoria") && (
                    <Segmentado
                      rotulo="Categoria"
                      opcoes={opcoesCategoria}
                      valor={filtros.categoria}
                      onChange={(categoria) => setFiltros((f) => ({ ...f, categoria }))}
                    />
                  )}
                  {relatorio.filtros.includes("horizonte") && (
                    <FiltroHorizonte valor={horizonteDe(filtros)} onChange={(horizonte) => setFiltros((f) => ({ ...f, horizonte }))} />
                  )}
                </div>
              )}
            </CardHeader>
            <CardContent className="px-0 pb-0">
              <div className="px-5 pb-2 text-xs flex items-center justify-between" style={{ color: "var(--muted-foreground)" }}>
                <span>
                  Prévia · {formatarNumero(Math.min(LINHAS_PREVIA, tabela.linhas.length))} de {formatarNumero(tabela.linhas.length)} linhas ·{" "}
                  {tabela.colunas.length} colunas
                </span>
              </div>
              <div className="overflow-x-auto border-t" style={{ borderColor: "var(--border)" }}>
                <Table>
                  <TableHeader>
                    <TableRow style={{ background: "var(--muted)" }}>
                      {tabela.colunas.map((c, i) => (
                        <TableHead
                          key={i}
                          className={`text-xs whitespace-nowrap ${i === 0 ? "pl-5" : ""} ${c.tipo === "numero" || c.tipo === "decimal" ? "text-right" : ""}`}
                        >
                          {c.titulo}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tabela.linhas.slice(0, LINHAS_PREVIA).map((l, j) => (
                      <TableRow key={j}>
                        {l.map((v, i) => {
                          const tipo = tabela.colunas[i]?.tipo ?? "texto";
                          return (
                            <TableCell
                              key={i}
                              className={`text-xs whitespace-nowrap ${i === 0 ? "pl-5" : ""} ${tipo === "numero" || tipo === "decimal" ? "text-right" : ""}`}
                            >
                              {formatarCelula(v, tipo)}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {tabela.linhas.length > LINHAS_PREVIA && (
                <p className="text-xs px-5 py-3 border-t" style={{ color: "var(--muted-foreground)", borderColor: "var(--border)" }}>
                  + {formatarNumero(tabela.linhas.length - LINHAS_PREVIA)} linhas no arquivo completo.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Histórico */}
          <Card className="border" style={{ borderColor: "var(--border)" }}>
            <CardHeader className="pb-2 pt-4 px-5 flex flex-row items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2" style={{ fontWeight: 600 }}>
                <History size={15} /> Baixados recentemente
              </CardTitle>
              {historico.length > 0 && (
                <Button variant="ghost" size="sm" className="gap-1 text-xs" style={{ color: "var(--muted-foreground)" }} onClick={() => setHistorico([])}>
                  <Trash2 size={12} /> Limpar
                </Button>
              )}
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {historico.length === 0 ? (
                <p className="text-xs py-2" style={{ color: "var(--muted-foreground)" }}>
                  Nenhum relatório baixado ainda. Os que você baixar aparecem aqui para baixar de novo com um clique.
                </p>
              ) : (
                <div className="flex flex-col divide-y" style={{ borderColor: "var(--border)" }}>
                  {historico.map((b) => (
                    <div key={b.id} className="flex items-center gap-3 py-2">
                      {b.formato === "pdf" ? (
                        <FileText size={15} style={{ color: "var(--primary)" }} />
                      ) : (
                        <FileSpreadsheet size={15} style={{ color: "var(--primary)" }} />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs truncate" style={{ fontWeight: 500 }}>
                          {b.titulo} <span style={{ color: "var(--muted-foreground)" }}>· {ROTULO_FORMATO[b.formato]}</span>
                        </p>
                        <p className="text-[11px] flex items-center gap-1" style={{ color: "var(--muted-foreground)" }}>
                          <Clock size={10} /> {new Date(b.quando).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })} ·{" "}
                          {descreverFiltros(relatorios.find((r) => r.id === b.relatorioId) ?? {}, b.filtros)}
                          {b.tamanho ? ` · ${formatarTamanhoArquivo(b.tamanho)}` : ""}
                        </p>
                      </div>
                      <Button variant="outline" size="sm" className="gap-1 text-xs h-7" onClick={() => rebaixar(b)}>
                        <Download size={12} /> De novo
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
