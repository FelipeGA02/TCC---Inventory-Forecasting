import { useEffect, useMemo, useState } from "react";
import { Check, CheckCircle2, ChevronsUpDown, Loader2, Scale, Target, TrendingUp, type LucideIcon } from "lucide-react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "../ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import type { CategoriaId, DiaHistoricoPrevisao, MetricasModelo, ProdutoDaLoja, StatusModelo, UnidadeId } from "@/domain/types";
import { CORES_CATEGORIA, categorias, nomeCategoria, produtosDe, unidades } from "../../data/mockData";
import { api } from "../../data/api";
import { mensagemDoErro } from "@/lib/http/errors";
import { Segmentado, StatusBadge } from "../shared";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDiaMes, formatarMesAno, formatarNumero, formatarQtd } from "@/lib/format";

/**
 * Aba "Histórico de previsão": para cada categoria e cada produto de grama de cada loja (cada
 * um com o seu modelo), o vendido (sem encomendas grandes) desde o começo da base × o
 * previsto congelado de cada dia — o que a previsão mostrava antes dele (`fonte = forecast`)
 * ou, nos dias que nenhuma previsão cobriu, o teste do treino com as vendas até a véspera
 * (`walk_forward`). Antes do 1º treino só há vendido. Os 4 indicadores são os do teste do
 * último treino.
 */

type Tipo = "categoria" | "produto";
/** "3m", "ano" (últimos 12 meses), "tudo" ou um mês "AAAA-MM". */
type Periodo = string;

const chave = (p: ProdutoDaLoja) => `${p.unidade}-${p.codigo}`;

// A série de cada item é buscada quando ele é aberto e guardada enquanto a tela existir.
const historicosBuscados = new Map<string, Promise<DiaHistoricoPrevisao[]>>();

function useHistorico(loja: UnidadeId, nivel: Tipo, item: string | undefined) {
  const [estado, setEstado] = useState<{ chave: string; serie?: DiaHistoricoPrevisao[]; erro?: string } | null>(null);
  const k = item ? `${loja}/${nivel}/${item}` : "";
  useEffect(() => {
    if (!item) return;
    let vivo = true;
    let busca = historicosBuscados.get(k);
    if (!busca) {
      busca = api.historico(loja, nivel, item);
      historicosBuscados.set(k, busca);
      busca.catch(() => historicosBuscados.delete(k));
    }
    busca
      .then((serie) => vivo && setEstado({ chave: k, serie }))
      .catch((e: unknown) => vivo && setEstado({ chave: k, erro: mensagemDoErro(e) }));
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k]);
  return estado?.chave === k ? estado : null;
}

// ---------------------------------------------------------------------------
// Indicadores em linguagem simples
// ---------------------------------------------------------------------------

const pct = (v: number) => `${formatarNumero(Math.round(v))}%`;
const acerto14d = (m: MetricasModelo) => (m.erro_total_14d_pct != null ? pct(Math.max(0, 100 - m.erro_total_14d_pct)) : "—");

function equilibrio(previstoSobreReal: number | null): string {
  if (previstoSobreReal == null) return "—";
  const d = previstoSobreReal - 100;
  if (Math.abs(d) < 3) return "na medida";
  return d > 0 ? `${pct(d)} acima` : `${pct(-d)} abaixo`;
}

const INDICADORES: { icone: LucideIcon; titulo: string; valor: (m: MetricasModelo) => string; explica: (m: MetricasModelo) => string }[] = [
  {
    icone: Target,
    titulo: "Acerto no total de 2 semanas",
    valor: acerto14d,
    explica: (m) => (m.erro_total_14d_pct != null ? `o total de 14 dias ficou, em média, ${pct(m.erro_total_14d_pct)} acima ou abaixo do vendido` : ""),
  },
  {
    icone: CheckCircle2,
    titulo: "Venda dentro da faixa",
    valor: (m) => pct(m.cobertura_ic95_pct),
    explica: () => "dos dias a venda ficou entre o mínimo e o máximo previstos",
  },
  {
    icone: TrendingUp,
    titulo: "Melhor que repetir a semana anterior",
    valor: (m) => `${m.rodadas_vence_naive} de ${m.rodadas}`,
    explica: (m) =>
      m.erro_relativo_naive != null ? `previsões de 2 semanas; no geral erra ${pct((1 - m.erro_relativo_naive) * 100)} menos` : "previsões de 2 semanas",
  },
  {
    icone: Scale,
    titulo: "Previsto x vendido",
    valor: (m) => equilibrio(m.previsto_sobre_real_pct),
    explica: () => "somando todo o período: se tende a exagerar ou a ficar curta",
  },
];

/** Título do tooltip: o dia e de onde veio o previsto dele. */
function rotuloDoDia(data: string, d: DiaHistoricoPrevisao | undefined): string {
  const partes = [formatarData(data)];
  if (d?.fonte === "forecast" && d.horizonte) partes.push(`previsto ${d.horizonte} dia${d.horizonte > 1 ? "s" : ""} antes`);
  if (d?.fonte === "walk_forward") partes.push("teste do treino, com as vendas até a véspera");
  if (d?.loja_fechada) partes.push("a previsão contava com a loja fechada");
  return partes.join(" · ");
}

// ---------------------------------------------------------------------------
// Período
// ---------------------------------------------------------------------------

const longo = (periodo: Periodo) => periodo === "ano" || periodo === "tudo";

function filtrarPeriodo(serie: DiaHistoricoPrevisao[], periodo: Periodo): DiaHistoricoPrevisao[] {
  if (periodo === "tudo" || serie.length === 0) return serie;
  if (periodo === "3m" || periodo === "ano") {
    const fim = new Date(`${serie[serie.length - 1]!.data}T12:00:00`);
    fim.setMonth(fim.getMonth() - (periodo === "3m" ? 3 : 12));
    const corte = fim.toISOString().slice(0, 10);
    return serie.filter((d) => d.data > corte);
  }
  return serie.filter((d) => d.data.startsWith(periodo));
}

/** Rótulos do eixo: um por mês (a cada 2 com mais de um ano); um por semana nos períodos curtos. */
function marcasEixo(datas: string[], periodo: Periodo): string[] {
  if (!longo(periodo)) return datas.filter((_, i) => i % 7 === 0);
  const meses = datas.filter((d, i) => i === 0 || d.slice(0, 7) !== datas[i - 1]!.slice(0, 7));
  return meses.length > 13 ? meses.filter((_, i) => i % 2 === 0) : meses;
}

// ---------------------------------------------------------------------------
// Tela
// ---------------------------------------------------------------------------

export function HistoricoPrevisao({ produtoSelecionado, onSelecionarProduto }: { produtoSelecionado: string | null; onSelecionarProduto: (k: string) => void }) {
  const [tipo, setTipo] = useState<Tipo>(produtoSelecionado ? "produto" : "categoria");
  // Vindo de "Ver histórico deste produto", abre na loja do produto (chave = "<loja>-<código>")
  const [lojaId, setLojaId] = useState<UnidadeId>(
    () => unidades.find((u) => produtoSelecionado?.startsWith(`${u.id}-`))?.id ?? unidades[0]!.id,
  );
  const [cat, setCat] = useState<CategoriaId>(categorias[0]!.id);
  const [periodo, setPeriodo] = useState<Periodo>("3m");

  // Mesmo recorte da tela de previsão: só os produtos de grama com previsão própria, da loja escolhida
  const produtos = useMemo(() => produtosDe(lojaId, "grama", true), [lojaId]);
  const produto = produtos.find((p) => chave(p) === produtoSelecionado) ?? produtos[0];
  const loja = unidades.find((u) => u.id === lojaId)!;
  const modeloCat = loja.categorias_modelo[cat];
  const comModelo = tipo === "categoria" ? !!modeloCat?.metricas : !!produto?.modelo.metricas;
  const historico = useHistorico(lojaId, tipo, !comModelo ? undefined : tipo === "categoria" ? cat : produto?.codigo);

  const meses = useMemo(() => [...new Set((historico?.serie ?? []).map((d) => d.data.slice(0, 7)))].reverse(), [historico]);
  const mesSelecionado = !["3m", "ano", "tudo"].includes(periodo) ? periodo : "";

  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardHeader className="pb-3 pt-4 px-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Histórico de previsão
          </CardTitle>
          <div className="flex items-center gap-4 flex-wrap">
            <Segmentado rotulo="Unidade" opcoes={unidades.map((u) => ({ valor: u.id, label: u.nome }))} valor={lojaId} onChange={setLojaId} />
            <Segmentado
              rotulo="Por"
              opcoes={[
                { valor: "categoria" as Tipo, label: "Categoria" },
                { valor: "produto" as Tipo, label: `Produto (${produtos.length})` },
              ]}
              valor={tipo}
              onChange={setTipo}
            />
          </div>
        </div>
        {/* Filtros numa linha inteira, como no "Dia a dia" da previsão */}
        <div className="mt-3 pt-3 border-t flex items-center gap-x-6 gap-y-2 flex-wrap" style={{ borderColor: "var(--border)" }}>
          {tipo === "categoria" && (
            <Segmentado rotulo="Categoria" opcoes={categorias.map((c) => ({ valor: c.id, label: c.nome }))} valor={cat} onChange={setCat} />
          )}
          {tipo === "produto" && <SeletorProduto produtos={produtos} produto={produto} onSelecionar={onSelecionarProduto} />}
          <div className="flex items-center gap-2 ml-auto">
            <Segmentado
              rotulo="Período"
              opcoes={[
                { valor: "3m", label: "Últimos 3 meses" },
                { valor: "ano", label: "Último ano" },
                { valor: "tudo", label: "Tudo" },
              ]}
              valor={periodo}
              onChange={setPeriodo}
            />
            <Select value={mesSelecionado} onValueChange={setPeriodo}>
              <SelectTrigger
                className="h-8 text-xs w-36"
                style={mesSelecionado ? { borderColor: "var(--primary)", color: "var(--primary)", fontWeight: 600 } : undefined}
              >
                <SelectValue placeholder="Escolher mês" />
              </SelectTrigger>
              <SelectContent>
                {meses.map((m) => (
                  <SelectItem key={m} value={m} className="text-xs">
                    {formatarMesAno(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="border-t min-w-0" style={{ borderColor: "var(--border)" }}>
          {!comModelo ? (
            <p className="text-xs p-8 text-center" style={{ color: "var(--muted-foreground)" }}>
              {tipo === "categoria"
                ? (modeloCat?.mensagem ?? "Esta categoria ficou sem previsão no último treino.")
                : produtos.length
                  ? "Selecione um produto."
                  : "Esta loja não tem produtos de grama com previsão no último treino."}
            </p>
          ) : !historico?.serie ? (
            <p className="text-xs p-8 flex items-center justify-center gap-2" style={{ color: historico?.erro ? "var(--destructive)" : "var(--muted-foreground)" }}>
              {historico?.erro ?? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Carregando o histórico...
                </>
              )}
            </p>
          ) : tipo === "categoria" ? (
            <PainelHistorico
              titulo={`${nomeCategoria(cat)} · ${loja.nome}`}
              subtitulo="previsão feita só com a venda da categoria nesta loja"
              status={modeloCat!.status}
              metricas={modeloCat!.metricas!}
              serie={historico.serie}
              periodo={periodo}
              cor={CORES_CATEGORIA[cat]}
              fmt={formatarNumero}
            />
          ) : (
            <PainelHistorico
              titulo={`${produto!.nome} · ${produto!.nomeUnidade}`}
              status={produto!.modelo.status}
              metricas={produto!.modelo.metricas!}
              serie={historico.serie}
              periodo={periodo}
              cor={CORES_CATEGORIA[produto!.categoria]}
              fmt={formatarQtd}
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Seletor de produto: lista com busca num menu, para o gráfico ocupar a largura toda
// ---------------------------------------------------------------------------

function SeletorProduto({
  produtos,
  produto,
  onSelecionar,
}: {
  produtos: ProdutoDaLoja[];
  produto: ProdutoDaLoja | undefined;
  onSelecionar: (k: string) => void;
}) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className="flex items-center gap-2 flex-1 min-w-[280px] max-w-[520px]">
      <span className="text-xs font-medium" style={{ color: "var(--muted-foreground)" }}>
        Produto
      </span>
      <Popover open={aberto} onOpenChange={setAberto}>
        <PopoverTrigger asChild>
          <button
            role="combobox"
            aria-expanded={aberto}
            className="flex-1 min-w-0 h-8 rounded-md border px-2.5 flex items-center gap-2 text-xs text-left hover:bg-[var(--muted)]"
            style={{ borderColor: "var(--border)", background: "var(--card)" }}
          >
            {produto ? (
              <>
                <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ background: CORES_CATEGORIA[produto.categoria] }} />
                <span className="truncate" style={{ fontWeight: 600 }}>
                  {produto.nome}
                </span>
                <span className="flex-shrink-0" style={{ color: "var(--muted-foreground)" }}>
                  cód. {produto.codigo}
                </span>
              </>
            ) : (
              <span style={{ color: "var(--muted-foreground)" }}>Nenhum produto</span>
            )}
            <ChevronsUpDown size={13} className="ml-auto flex-shrink-0" style={{ color: "var(--muted-foreground)" }} />
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="p-0 w-[var(--radix-popover-trigger-width)] min-w-[320px]">
          <Command>
            <CommandInput placeholder="Buscar produto ou código" className="text-xs" />
            <CommandList>
              <CommandEmpty className="py-6 text-center text-xs" style={{ color: "var(--muted-foreground)" }}>
                Nenhum produto encontrado.
              </CommandEmpty>
              <CommandGroup>
                {produtos.map((p) => {
                  const ativo = produto && chave(produto) === chave(p);
                  const m = p.modelo.metricas;
                  return (
                    <CommandItem
                      key={chave(p)}
                      value={`${p.nome} ${p.codigo}`}
                      onSelect={() => {
                        onSelecionar(chave(p));
                        setAberto(false);
                      }}
                      className="text-xs"
                    >
                      <Check size={13} className="flex-shrink-0" style={{ opacity: ativo ? 1 : 0, color: "var(--primary)" }} />
                      <span className="flex-1 min-w-0">
                        <span className="block truncate" style={{ fontWeight: ativo ? 700 : 500 }}>
                          {p.nome}
                        </span>
                        <span className="block text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                          cód. {p.codigo}
                        </span>
                      </span>
                      <span className="text-right flex-shrink-0">
                        <span className="block" style={{ fontWeight: 700 }}>
                          {m ? acerto14d(m) : "—"}
                        </span>
                        <span className="block text-[10px]" style={{ color: "var(--muted-foreground)" }}>
                          acerto
                        </span>
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Painel: indicadores do período testado + gráfico diário
// ---------------------------------------------------------------------------

function PainelHistorico({
  titulo,
  subtitulo,
  status,
  metricas,
  serie,
  periodo,
  cor,
  fmt,
}: {
  titulo: string;
  subtitulo?: string;
  status: StatusModelo;
  metricas: MetricasModelo;
  serie: DiaHistoricoPrevisao[];
  periodo: Periodo;
  cor: string;
  fmt: (v: number) => string;
}) {
  // O previsto em duas linhas: o que a tela mostrava (congelado) e o teste do treino, nos
  // dias que nenhuma previsão cobriu (antes do 1º treino, ou intervalo maior que 14 dias)
  const dadosGrafico = useMemo(
    () =>
      filtrarPeriodo(serie, periodo).map((d) => ({
        ...d,
        previsto_tela: d.fonte === "forecast" ? d.previsto : null,
        previsto_teste: d.fonte === "walk_forward" ? d.previsto : null,
        faixa: d.inf != null && d.sup != null ? ([d.inf, d.sup] as [number, number]) : null,
      })),
    [serie, periodo],
  );
  // 1º dia com previsto: a data fixa de treino (antes dela, o modelo ainda estava aprendendo)
  const inicioPrevisto = serie.find((d) => d.previsto != null)?.data;
  const marcaInicio = inicioPrevisto && dadosGrafico.some((d) => d.data === inicioPrevisto) && dadosGrafico[0]!.data !== inicioPrevisto;

  return (
    <div className="p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            {titulo}
          </p>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            {subtitulo ? `${subtitulo}. ` : ""}
            {inicioPrevisto
              ? `O previsto começa em ${formatarData(inicioPrevisto)}: até ali o modelo aprendia com as vendas. Cada dia mostra o que a previsão dizia antes dele; nos dias que nenhuma previsão cobriu, o teste do treino com as vendas até a véspera.`
              : "O previsto ainda não foi gravado: aparece depois do próximo treino."}
          </p>
        </div>
        <StatusBadge status={status} compacto />
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {INDICADORES.map((ind) => {
          const Icone = ind.icone;
          return (
            <div key={ind.titulo} className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
              <p className="text-[11px] inline-flex items-center gap-1.5" style={{ color: "var(--muted-foreground)", fontWeight: 600 }}>
                <Icone size={13} style={{ color: "var(--primary)" }} /> {ind.titulo}
              </p>
              <p className="text-xl mt-0.5" style={{ fontWeight: 700 }}>
                {ind.valor(metricas)}
              </p>
              <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                {ind.explica(metricas)}
              </p>
            </div>
          );
        })}
      </div>

      {serie.length === 0 ? (
        <p className="text-xs text-center py-10 rounded-lg" style={{ color: "var(--muted-foreground)", background: "var(--background)" }}>
          Sem vendas no período.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-4 text-xs flex-wrap" style={{ color: "var(--muted-foreground)" }}>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido (sem encomendas grandes)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5" style={{ background: cor }} /> Previsto (o que a tela mostrava)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: cor }} /> Previsto no teste do treino
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: cor, opacity: 0.18 }} /> Faixa prevista
            </span>
          </div>
          <ResponsiveContainer width="100%" height={340}>
            <ComposedChart data={dadosGrafico} margin={{ top: 5, right: 24, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="data"
                ticks={marcasEixo(
                  dadosGrafico.map((d) => d.data),
                  periodo,
                )}
                tickFormatter={(d: string) => (longo(periodo) ? formatarMesAno(d) : formatarDiaMes(d))}
                tick={eixo}
                tickLine={false}
                axisLine={false}
                interval={0}
              />
              <YAxis tick={eixo} width={56} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
              <Tooltip
                contentStyle={estiloTooltip}
                labelFormatter={(d: string, itens: { payload?: DiaHistoricoPrevisao }[]) => rotuloDoDia(d, itens?.[0]?.payload)}
                formatter={(v: number | [number, number], nome: string) =>
                  nome === "faixa" && Array.isArray(v)
                    ? [`${fmt(v[0])} a ${fmt(v[1])}`, "Faixa prevista"]
                    : [fmt(v as number), nome === "real" ? "Vendido" : nome === "previsto_teste" ? "Previsto no teste" : "Previsto"]
                }
              />
              {marcaInicio && (
                <ReferenceLine
                  x={inicioPrevisto}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={{ value: "início da previsão", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }}
                />
              )}
              <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.15} isAnimationActive={false} />
              <Line dataKey="real" stroke="var(--foreground)" strokeWidth={1.5} dot={!longo(periodo) ? { r: 2 } : false} isAnimationActive={false} />
              <Line dataKey="previsto_tela" stroke={cor} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line dataKey="previsto_teste" stroke={cor} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
