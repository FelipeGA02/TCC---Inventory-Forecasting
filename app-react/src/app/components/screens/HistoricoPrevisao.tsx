import { useMemo, useState } from "react";
import { CheckCircle2, Scale, Search, Target, TrendingUp, type LucideIcon } from "lucide-react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import type { CategoriaId, DiaBacktest, MetricasModelo, ProdutoDaLoja, StatusModelo, UnidadeId } from "@/domain/types";
import { CORES_CATEGORIA, COR_TOTAL, categorias, nomeCategoria, produtosDe, unidades } from "../../data/mockData";
import { Segmentado, StatusBadge } from "../shared";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDiaMes, formatarMesAno, formatarNumero, formatarQtd } from "@/lib/format";

/**
 * Aba "Ver histórico de previsão": para cada previsão feita — a de cada loja, a de cada
 * categoria em cada loja (desagregação) e a de cada produto com previsão própria — o que foi
 * previsto × o que foi vendido, dia a dia, com 4 indicadores em linguagem simples.
 */

type Tipo = "loja" | "categoria" | "produto";
/** "3m", "ano" ou um mês "AAAA-MM". */
type Periodo = string;

const chave = (p: ProdutoDaLoja) => `${p.unidade}-${p.codigo}`;

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

// ---------------------------------------------------------------------------
// Período
// ---------------------------------------------------------------------------

function filtrarPeriodo(serie: DiaBacktest[], periodo: Periodo): DiaBacktest[] {
  if (periodo === "ano" || serie.length === 0) return serie;
  if (periodo === "3m") {
    const fim = new Date(`${serie[serie.length - 1]!.data}T12:00:00`);
    fim.setMonth(fim.getMonth() - 3);
    const corte = fim.toISOString().slice(0, 10);
    return serie.filter((d) => d.data > corte);
  }
  return serie.filter((d) => d.data.startsWith(periodo));
}

/** Rótulos do eixo: um por mês no ano inteiro; um por semana nos períodos curtos. */
function marcasEixo(datas: string[], periodo: Periodo): string[] {
  if (periodo === "ano") return datas.filter((d, i) => i === 0 || d.slice(0, 7) !== datas[i - 1]!.slice(0, 7));
  return datas.filter((_, i) => i % 7 === 0);
}

// ---------------------------------------------------------------------------
// Tela
// ---------------------------------------------------------------------------

export function HistoricoPrevisao({ produtoSelecionado, onSelecionarProduto }: { produtoSelecionado: string | null; onSelecionarProduto: (k: string) => void }) {
  const [tipo, setTipo] = useState<Tipo>(produtoSelecionado ? "produto" : "loja");
  const [lojaId, setLojaId] = useState<UnidadeId>(unidades[0]!.id);
  const [cat, setCat] = useState<CategoriaId>(categorias[0]!.id);
  const [periodo, setPeriodo] = useState<Periodo>("3m");
  const [busca, setBusca] = useState("");

  const produtos = useMemo(() => produtosDe("todas", "todas", true), []);
  const visiveis = useMemo(() => {
    const t = busca.trim().toLowerCase();
    return t ? produtos.filter((p) => p.nome.toLowerCase().includes(t) || p.codigo.includes(t)) : produtos;
  }, [produtos, busca]);
  const produto = produtos.find((p) => chave(p) === produtoSelecionado) ?? produtos[0];
  const loja = unidades.find((u) => u.id === lojaId)!;
  const desag = loja.desagregacao?.[cat];

  const meses = useMemo(() => [...new Set(unidades[0]!.backtest.map((d) => d.data.slice(0, 7)))], []);
  const mesSelecionado = periodo !== "3m" && periodo !== "ano" ? periodo : "";

  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardHeader className="pb-3 pt-4 px-5 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Histórico de previsão
          </CardTitle>
          <Segmentado
            rotulo="Previsão da"
            opcoes={[
              { valor: "loja" as Tipo, label: "Loja" },
              { valor: "categoria" as Tipo, label: "Categoria" },
              { valor: "produto" as Tipo, label: `Produto (${produtos.length})` },
            ]}
            valor={tipo}
            onChange={setTipo}
          />
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          {tipo !== "produto" && (
            <Segmentado rotulo="Loja" opcoes={unidades.map((u) => ({ valor: u.id, label: u.nome }))} valor={lojaId} onChange={setLojaId} />
          )}
          {tipo === "categoria" && (
            <Segmentado rotulo="Categoria" opcoes={categorias.map((c) => ({ valor: c.id, label: c.nome }))} valor={cat} onChange={setCat} />
          )}
          <div className="flex items-center gap-2 ml-auto">
            <Segmentado
              rotulo="Período"
              opcoes={[
                { valor: "3m", label: "Últimos 3 meses" },
                { valor: "ano", label: "Ano inteiro" },
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
        {tipo === "loja" && (
          <div className="border-t" style={{ borderColor: "var(--border)" }}>
            <PainelHistorico
              titulo={`${loja.nome} · loja inteira, sem encomendas`}
              status={loja.modelo.status}
              metricas={loja.modelo.metricas}
              serie={loja.backtest}
              periodo={periodo}
              cor={COR_TOTAL}
              fmt={formatarNumero}
            />
          </div>
        )}
        {tipo === "categoria" && (
          <div className="border-t" style={{ borderColor: "var(--border)" }}>
            {desag ? (
              <PainelHistorico
                titulo={`${nomeCategoria(cat)} · ${loja.nome}`}
                subtitulo="parte da categoria na previsão da loja, pelo que vendeu nas 8 semanas anteriores em cada dia da semana"
                status={desag.status}
                metricas={desag.metricas}
                serie={desag.backtest}
                periodo={periodo}
                cor={CORES_CATEGORIA[cat]}
                fmt={formatarNumero}
              />
            ) : (
              <p className="text-xs p-8 text-center" style={{ color: "var(--muted-foreground)" }}>
                O histórico das categorias ainda não foi gerado.
              </p>
            )}
          </div>
        )}
        {tipo === "produto" && (
          <div className="grid grid-cols-1 xl:grid-cols-[320px_minmax(0,1fr)] border-t" style={{ borderColor: "var(--border)" }}>
            <div className="border-b xl:border-b-0 xl:border-r flex flex-col" style={{ borderColor: "var(--border)" }}>
              <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
                <div className="relative">
                  <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
                  <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar produto ou código" className="h-8 text-xs pl-8" />
                </div>
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: 560 }}>
                {visiveis.map((p) => {
                  const ativo = produto && chave(produto) === chave(p);
                  const m = p.modelo?.metricas;
                  return (
                    <button
                      key={chave(p)}
                      onClick={() => onSelecionarProduto(chave(p))}
                      className="w-full text-left px-4 py-2.5 flex items-center gap-3 border-b hover:bg-[var(--muted)]"
                      style={{ borderColor: "var(--border)", background: ativo ? "var(--secondary)" : undefined }}
                    >
                      <span className="w-1 self-stretch rounded-full" style={{ background: ativo ? CORES_CATEGORIA[p.categoria] : "transparent" }} />
                      <span className="flex-1 min-w-0">
                        <span className="block text-xs truncate" style={{ fontWeight: 500 }}>
                          {p.nome}
                        </span>
                        <span className="block text-[11px] truncate" style={{ color: "var(--muted-foreground)" }}>
                          {nomeCategoria(p.categoria)} · {p.nomeUnidade}
                        </span>
                      </span>
                      <span className="text-right">
                        <span className="block text-xs" style={{ fontWeight: 700 }}>
                          {m ? acerto14d(m) : "—"}
                        </span>
                        <span className="block text-[10px]" style={{ color: "var(--muted-foreground)" }}>
                          acerto
                        </span>
                      </span>
                    </button>
                  );
                })}
                {visiveis.length === 0 && (
                  <p className="text-xs text-center py-8" style={{ color: "var(--muted-foreground)" }}>
                    Nenhum produto encontrado.
                  </p>
                )}
              </div>
            </div>
            <div className="min-w-0">
              {produto && produto.modelo?.metricas ? (
                <PainelHistorico
                  titulo={`${produto.nome} · ${produto.nomeUnidade}`}
                  status={produto.modelo.status}
                  metricas={produto.modelo.metricas}
                  serie={produto.backtest ?? []}
                  periodo={periodo}
                  cor={CORES_CATEGORIA[produto.categoria]}
                  fmt={formatarQtd}
                />
              ) : (
                <p className="text-xs p-8 text-center" style={{ color: "var(--muted-foreground)" }}>
                  Selecione um produto.
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
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
  serie: DiaBacktest[];
  periodo: Periodo;
  cor: string;
  fmt: (v: number) => string;
}) {
  const dadosGrafico = useMemo(() => filtrarPeriodo(serie, periodo).map((d) => ({ ...d, faixa: [d.inf, d.sup] as [number, number] })), [serie, periodo]);
  const testado = serie.length ? `${formatarMesAno(serie[0]!.data)} a ${formatarMesAno(serie[serie.length - 1]!.data)}` : "";

  return (
    <div className="p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            {titulo}
          </p>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            {subtitulo ? `${subtitulo}. ` : ""}Indicadores de todo o período testado{testado ? ` (${testado})` : ""}, sempre prevendo as 2 semanas seguintes com o
            que se sabia até ali.
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
          O histórico dia a dia ainda não foi gerado.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-4 text-xs flex-wrap" style={{ color: "var(--muted-foreground)" }}>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5" style={{ background: cor }} /> Previsto
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
                tickFormatter={(d: string) => (periodo === "ano" ? formatarMesAno(d) : formatarDiaMes(d))}
                tick={eixo}
                tickLine={false}
                axisLine={false}
                interval={0}
              />
              <YAxis tick={eixo} width={56} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
              <Tooltip
                contentStyle={estiloTooltip}
                labelFormatter={(d: string) => formatarData(d)}
                formatter={(v: number | [number, number], nome: string) =>
                  nome === "faixa" && Array.isArray(v)
                    ? [`${fmt(v[0])} a ${fmt(v[1])}`, "Faixa prevista"]
                    : [fmt(v as number), nome === "real" ? "Vendido" : "Previsto"]
                }
              />
              <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.15} isAnimationActive={false} />
              <Line dataKey="real" stroke="var(--foreground)" strokeWidth={1.5} dot={periodo !== "ano" ? { r: 2 } : false} isAnimationActive={false} />
              <Line dataKey="previsto" stroke={cor} strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
