import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import type { UnidadeDados, UnidadeId } from "@/domain/types";
import { LIMIAR_ENCOMENDA, dados, nomeCategoria, produtosDe, unidades, unidadesDoFiltro } from "../../data/mockData";
import { MarcaCategoria, Segmentado, StatusBadge, useFiltroLoja } from "../shared";
import { eixo, estiloStatus, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDecimal, formatarDiaMes, formatarNumero, formatarPercentual } from "@/lib/format";

type Periodo = "trimestre" | "ano";
const COR_MODELO = "#1a6b3c";
const COR_NAIVE = "#8b96a8";

function Criterio({ ok, titulo, valor, meta, explicacao }: { ok: boolean; titulo: string; valor: string; meta: string; explicacao: string }) {
  return (
    <div className="rounded-lg p-3 flex flex-col gap-1" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs" style={{ color: "var(--muted-foreground)", fontWeight: 500 }}>
          {titulo}
        </span>
        {ok ? <CheckCircle2 size={14} color="#1a6b3c" aria-label="atende" /> : <AlertTriangle size={14} color="#b77800" aria-label="não atende" />}
      </div>
      <p className="text-xl" style={{ fontWeight: 700, lineHeight: 1.1 }}>
        {valor}
      </p>
      <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
        {explicacao}
      </p>
      <p className="text-[11px]" style={{ color: ok ? "#1a6b3c" : "#8a5a00", fontWeight: 600 }}>
        Meta: {meta}
      </p>
    </div>
  );
}

function CartaoLoja({ u }: { u: UnidadeDados }) {
  const m = u.modelo.metricas;
  const ganho = 1 - (m.erro_relativo_naive ?? 1);
  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardHeader className="pb-2 pt-4 px-5">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            {u.nome} · previsão da loja
          </CardTitle>
          <StatusBadge status={u.modelo.status} />
        </div>
        <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
          {estiloStatus[u.modelo.status].explicacao}
        </p>
      </CardHeader>
      <CardContent className="px-5 pb-5 flex flex-col gap-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Criterio ok={m.mase < 1} titulo="MASE" valor={formatarDecimal(m.mase)} meta="abaixo de 1,00" explicacao="Abaixo de 1 = erra menos que o naive sazonal no histórico." />
          <Criterio
            ok={90 <= m.cobertura_ic95_pct && m.cobertura_ic95_pct <= 98}
            titulo="Cobertura do intervalo de 95%"
            valor={`${formatarDecimal(m.cobertura_ic95_pct, 1)}%`}
            meta="entre 90% e 98%"
            explicacao="Dias em que a venda ficou dentro do intervalo."
          />
          <Criterio
            ok={ganho > 0}
            titulo="Contra o naive sazonal"
            valor={`${formatarPercentual(ganho)} menos erro`}
            meta="menos erro que o naive"
            explicacao={`Venceu em ${m.rodadas_vence_naive} de ${m.rodadas} rodadas de teste.`}
          />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs" style={{ color: "var(--muted-foreground)" }}>
          {[
            ["Erro médio por dia", formatarNumero(m.mae)],
            ["Largura média do intervalo", formatarNumero(m.largura_ic95)],
            ["Volume previsto ÷ vendido", m.previsto_sobre_real_pct != null ? `${formatarDecimal(m.previsto_sobre_real_pct, 1)}%` : "—"],
            ["Dias testados", formatarNumero(m.dias_avaliados)],
          ].map(([r, v]) => (
            <div key={r}>
              <p>{r}</p>
              <p className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                {v}
              </p>
            </div>
          ))}
        </div>
        <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
          Modelo: SARIMAX({u.modelo.ordem.join(",")})({u.modelo.ordem_sazonal.join(",")}) na venda sem encomendas (nota acima de{" "}
          {formatarNumero(LIMIAR_ENCOMENDA)} un.), sem transformação, janela deslizante de {u.modelo.janela_dias} dias · calendário da loja
          (dia da semana, loja fechada, abertura excepcional)
        </p>
      </CardContent>
    </Card>
  );
}

/** Conteúdo da aba "Como a previsão foi testada" da tela Previsão de Vendas. */
export function AcertoConteudo() {
  const { unidade, categoria } = useFiltroLoja();
  const lojas = unidadesDoFiltro(unidade);
  const [lojaGrafico, setLojaGrafico] = useState<UnidadeId>(lojas[0]!.id);
  const [periodo, setPeriodo] = useState<Periodo>("trimestre");
  const loja = unidade === "todas" ? unidades.find((u) => u.id === lojaGrafico)! : lojas[0]!;

  const serie = useMemo(() => {
    const bt = periodo === "ano" ? loja.backtest : loja.backtest.slice(-91);
    return bt.map((d) => ({ ...d, faixa: [d.inf, d.sup] as [number, number] }));
  }, [loja, periodo]);
  const regulares = useMemo(
    () => produtosDe(unidade, categoria, true).filter((p) => p.modelo?.metricas).sort((a, b) => a.categoria.localeCompare(b.categoria) || a.modelo!.metricas!.mase - b.modelo!.metricas!.mase),
    [unidade, categoria],
  );
  const cfg = dados.configuracao;
  const passam = regulares.filter((p) => p.modelo!.status === "trained").length;
  const vencem = regulares.filter((p) => (p.modelo!.metricas!.erro_relativo_naive ?? 1) < 1).length;

  return (
    <div className="flex flex-col gap-5">
      <Card className="border" style={{ borderColor: "var(--border)", background: "var(--secondary)" }}>
        <CardContent className="p-4 text-xs leading-relaxed" style={{ color: "var(--secondary-foreground)" }}>
          <strong>Como a previsão foi testada:</strong> o sistema voltou no tempo {loja.modelo.rodadas.length} vezes, de{" "}
          {formatarData(cfg.primeira_origem_validacao)} a {formatarData(loja.backtest[loja.backtest.length - 1]!.data)}, a cada {cfg.passo_origem_dias} dias.
          Em cada volta, usou só as vendas anteriores para prever os {cfg.horizonte_dias} dias seguintes e comparou com o que foi vendido. A régua é o
          naive sazonal: vender o mesmo que no mesmo dia da semana anterior. A previsão da loja e a de cada produto regular foram testadas assim; as
          encomendas ficam de fora porque não seguem o padrão do dia a dia.
        </CardContent>
      </Card>

      <div className={`grid grid-cols-1 ${lojas.length > 1 ? "2xl:grid-cols-2" : ""} gap-4`}>
        {lojas.map((u) => (
          <CartaoLoja key={u.id} u={u} />
        ))}
      </div>

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-1 pt-4 px-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                Previsto × vendido nos testes · {loja.nome} · loja inteira, sem encomendas
              </CardTitle>
              <div className="flex items-center gap-4 text-xs mt-1 flex-wrap" style={{ color: "var(--muted-foreground)" }}>
                <span className="inline-flex items-center gap-1.5">
                  <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="inline-block w-4 h-0.5" style={{ background: COR_MODELO }} /> Previsto
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: COR_MODELO, opacity: 0.18 }} /> Intervalo de 95%
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              {unidade === "todas" && (
                <Segmentado rotulo="Loja" opcoes={unidades.map((u) => ({ valor: u.id, label: u.nome }))} valor={lojaGrafico} onChange={setLojaGrafico} />
              )}
              <Segmentado
                rotulo="Período"
                opcoes={[
                  { valor: "trimestre" as Periodo, label: "Últimos 3 meses" },
                  { valor: "ano" as Periodo, label: "Ano inteiro" },
                ]}
                valor={periodo}
                onChange={setPeriodo}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-4">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={serie}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} minTickGap={24} />
              <YAxis tick={eixo} width={60} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
              <Tooltip
                contentStyle={estiloTooltip}
                labelFormatter={(d: string) => formatarData(d)}
                formatter={(v: number | [number, number], nome: string) =>
                  nome === "faixa" && Array.isArray(v) ? [`${formatarNumero(v[0])} a ${formatarNumero(v[1])}`, "Intervalo de 95%"] : [formatarNumero(v as number), nome === "real" ? "Vendido" : "Previsto"]
                }
              />
              <Area dataKey="faixa" stroke="none" fill={COR_MODELO} fillOpacity={0.18} isAnimationActive={false} />
              <Line dataKey="real" stroke="var(--foreground)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
              <Line dataKey="previsto" stroke={COR_MODELO} strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-1 pt-4 px-5">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Erro em cada rodada de teste · {loja.nome}
          </CardTitle>
          <div className="flex items-center gap-4 text-xs mt-1 flex-wrap" style={{ color: "var(--muted-foreground)" }}>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COR_MODELO }} /> Previsão
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COR_NAIVE }} /> Naive sazonal
            </span>
            <span>· soma do erro nos 14 dias; menor é melhor</span>
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-4">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={loja.modelo.rodadas} barGap={2} barCategoryGap="22%">
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="origem" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={1} />
              <YAxis tick={eixo} width={60} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
              <Tooltip
                contentStyle={estiloTooltip}
                cursor={{ fill: "rgba(26,107,60,0.06)" }}
                labelFormatter={(d: string) => `Rodada iniciada em ${formatarData(d)}`}
                formatter={(v: number, nome: string) => [formatarNumero(v), nome === "erro_modelo" ? "Previsão" : "Naive sazonal"]}
              />
              <Bar dataKey="erro_modelo" fill={COR_MODELO} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="erro_naive" fill={COR_NAIVE} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Produtos regulares · {nomeCategoria(categoria)} · um modelo por produto
          </CardTitle>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
            {regulares.length} produtos · {passam} passam no critério do projeto (MASE abaixo de 1 e intervalo acertando de 90% a 98%) · {vencem} erram
            menos que o naive sazonal nos dias de teste
          </p>
        </CardHeader>
        <CardContent className="px-0 pb-2 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5">Produto</TableHead>
                {unidade === "todas" && <TableHead className="text-xs">Loja</TableHead>}
                <TableHead className="text-xs">Categoria</TableHead>
                <TableHead className="text-xs text-right">MASE</TableHead>
                <TableHead className="text-xs text-right">Cobertura</TableHead>
                <TableHead className="text-xs text-right" title="Volume previsto ÷ volume vendido">Viés</TableHead>
                <TableHead className="text-xs text-right" title="Erro no total de 14 dias do produto">Erro 14 dias</TableHead>
                <TableHead className="text-xs text-right" title="Rodadas em que errou menos que o naive sazonal">Vence naive</TableHead>
                <TableHead className="text-xs pr-5">Situação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {regulares.map((p) => {
                const m = p.modelo!.metricas!;
                return (
                  <TableRow key={`${p.unidade}-${p.codigo}`}>
                    <TableCell className="text-xs pl-5">
                      <p style={{ fontWeight: 500 }}>{p.nome}</p>
                      <p style={{ color: "var(--muted-foreground)" }}>cód. {p.codigo}</p>
                    </TableCell>
                    {unidade === "todas" && <TableCell className="text-xs">{p.nomeUnidade}</TableCell>}
                    <TableCell className="text-xs">
                      <span className="inline-flex items-center gap-1.5">
                        <MarcaCategoria id={p.categoria} tamanho={8} /> {nomeCategoria(p.categoria)}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-right" style={{ fontWeight: 600, color: m.mase < 1 ? "var(--foreground)" : "#8a5a00" }}>
                      {formatarDecimal(m.mase)}
                    </TableCell>
                    <TableCell className="text-xs text-right">{formatarDecimal(m.cobertura_ic95_pct, 1)}%</TableCell>
                    <TableCell className="text-xs text-right">{m.previsto_sobre_real_pct != null ? `${formatarNumero(m.previsto_sobre_real_pct)}%` : "—"}</TableCell>
                    <TableCell className="text-xs text-right">{m.erro_total_14d_pct != null ? `${formatarNumero(m.erro_total_14d_pct)}%` : "—"}</TableCell>
                    <TableCell className="text-xs text-right">
                      {m.rodadas_vence_naive} de {m.rodadas}
                    </TableCell>
                    <TableCell className="pr-5">
                      <StatusBadge status={p.modelo!.status} compacto />
                    </TableCell>
                  </TableRow>
                );
              })}
              {regulares.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-xs text-center py-6" style={{ color: "var(--muted-foreground)" }}>
                    Nenhum produto regular com teste nesta seleção.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
