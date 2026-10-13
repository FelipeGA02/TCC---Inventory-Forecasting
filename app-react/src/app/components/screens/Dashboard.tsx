import { useMemo } from "react";
import { useNavigate } from "react-router";
import { CalendarRange, Database, ShieldCheck, TrendingUp, ArrowRight } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import {
  CORES_CATEGORIA,
  HORIZONTE_DIAS,
  categorias,
  dados,
  historicoDiarioDe,
  historicoSemanalDe,
  nomeCategoria,
  previsaoDe,
  produtosDe,
  semanasPrevistasDe,
  somar,
  unidadesDoFiltro,
} from "../../data/mockData";
import { FiltroLoja, Kpi, LegendaCategorias, MarcaCategoria, MiniBarras, StatusBadge, useFiltroLoja } from "../shared";
import { eixo, estiloTooltip } from "@/styles/tokens";
import {
  formatarData,
  formatarDiaMes,
  formatarDiaMesCurto,
  formatarNumero,
  formatarPercentual,
  formatarQtd,
} from "@/lib/format";

const SEMANAS_HISTORICO = 16;

export function Dashboard() {
  const { unidade } = useFiltroLoja();
  const navigate = useNavigate();

  const previsao = useMemo(() => previsaoDe(unidade), [unidade]);
  const historico = useMemo(() => historicoDiarioDe(unidade), [unidade]);
  const lojas = unidadesDoFiltro(unidade);

  const total14 = somar(previsao.map((d) => d.previsto));
  const inf14 = somar(previsao.map((d) => d.inf));
  const sup14 = somar(previsao.map((d) => d.sup));
  const diasAbertos = previsao.filter((d) => !d.loja_fechada).length;
  // Mesmo período de 14 dias logo antes da previsão, para comparar.
  const ultimos14 = historico.slice(-HORIZONTE_DIAS);
  const real14 = somar(ultimos14.map((d) => d.total));
  const variacao = real14 > 0 ? total14 / real14 - 1 : 0;

  const grafico = useMemo(() => {
    const hist = historicoSemanalDe(unidade).slice(-SEMANAS_HISTORICO);
    const datasHist = new Set(hist.map((s) => s.semana));
    const prev = semanasPrevistasDe(unidade).filter((s) => !datasHist.has(s.semana));
    return [
      ...hist.map((s) => ({ semana: s.semana, tipo: "real" as const, total: s.total, ...s.categorias })),
      ...prev.map((s) => ({ semana: s.semana, tipo: "previsto" as const, total: s.total, ...s.categorias })),
    ];
  }, [unidade]);
  const primeiraPrevista = grafico.find((g) => g.tipo === "previsto")?.semana;

  const porCategoria = categorias.map((c) => {
    const prev = somar(previsao.map((d) => d.categorias[c.id].previsto));
    const real = somar(ultimos14.map((d) => d.categorias[c.id]));
    return { ...c, prev, real, participacao: total14 ? prev / total14 : 0 };
  });

  const topProdutos = useMemo(
    () => produtosDe(unidade).sort((a, b) => b.previsao_14d - a.previsao_14d).slice(0, 8),
    [unidade],
  );

  const inicio = previsao[0]!.data;
  const fim = previsao[previsao.length - 1]!.data;

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <FiltroLoja />
        <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          Vendas registradas até <strong>{formatarData(dados.base.fim)}</strong> · previsão de{" "}
          <strong>{formatarDiaMes(inicio)}</strong> a <strong>{formatarDiaMes(fim)}</strong>
        </p>
      </div>

      {/* Indicadores */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Kpi
          icone={TrendingUp}
          rotulo={`Venda prevista · próximos ${HORIZONTE_DIAS} dias`}
          valor={formatarNumero(total14)}
          detalhe={
            <>
              Faixa provável: {formatarNumero(inf14)} a {formatarNumero(sup14)}
              <br />
              {variacao >= 0 ? "▲" : "▼"} {formatarPercentual(Math.abs(variacao))}{" "}
              {variacao >= 0 ? "acima" : "abaixo"} dos últimos 14 dias ({formatarNumero(real14)})
            </>
          }
        />
        <Kpi
          icone={CalendarRange}
          rotulo="Média por dia de loja aberta"
          valor={formatarNumero(total14 / Math.max(1, diasAbertos))}
          detalhe={`${diasAbertos} dias abertos no período · domingos e feriados fechados`}
        />
        <Kpi
          icone={ShieldCheck}
          rotulo="Confiança da previsão"
          valor={
            <div className="flex flex-col gap-1.5">
              {lojas.map((l) => (
                <div key={l.id} className="flex items-center justify-between gap-2 text-sm" style={{ fontWeight: 500 }}>
                  <span>{l.nome}</span>
                  <StatusBadge status={l.modelo.status} compacto />
                </div>
              ))}
            </div>
          }
          rodape={
            <button
              className="text-xs text-left underline-offset-2 hover:underline"
              style={{ color: "var(--primary)", fontWeight: 500 }}
              onClick={() => navigate("/acerto")}
            >
              Ver como a previsão foi testada →
            </button>
          }
        />
        <Kpi
          icone={Database}
          rotulo="Linhas de venda analisadas"
          valor={formatarNumero(dados.base.linhas)}
          detalhe={`${formatarNumero(dados.base.skus)} produtos · ${formatarData(dados.base.inicio)} a ${formatarData(dados.base.fim)}`}
        />
      </div>

      {/* Tendência semanal */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-1 pt-5 px-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                Vendas por semana · últimas {SEMANAS_HISTORICO} semanas e as 2 próximas
              </CardTitle>
              <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                Barras claras = previsão. Quantidade somada em todas as unidades de venda (m², bandeja, saco, unidade).
              </p>
            </div>
            <LegendaCategorias />
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-4">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={grafico} barCategoryGap="18%">
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="semana" tickFormatter={formatarDiaMesCurto} tick={eixo} tickLine={false} axisLine={false} interval={1} />
              <YAxis tick={eixo} tickFormatter={(v: number) => formatarNumero(v)} width={56} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={estiloTooltip}
                cursor={{ fill: "rgba(26,107,60,0.06)" }}
                labelFormatter={(s: string, p) =>
                  `${p?.[0]?.payload?.tipo === "previsto" ? "Previsão · " : ""}semana de ${formatarData(s)}`
                }
                formatter={(v: number, nome: string) => [formatarNumero(v), nomeCategoria(nome as never)]}
              />
              {primeiraPrevista && (
                <ReferenceLine x={primeiraPrevista} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "previsão", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
              )}
              {categorias.map((c, i) => (
                <Bar
                  key={c.id}
                  dataKey={c.id}
                  stackId="v"
                  fill={CORES_CATEGORIA[c.id]}
                  stroke="#fff"
                  strokeWidth={1}
                  radius={i === categorias.length - 1 ? [4, 4, 0, 0] : 0}
                  isAnimationActive={false}
                >
                  {grafico.map((g) => (
                    <Cell key={g.semana} fillOpacity={g.tipo === "previsto" ? 0.4 : 1} />
                  ))}
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Categorias */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {porCategoria.map((c) => {
          const delta = c.real > 0 ? c.prev / c.real - 1 : 0;
          return (
            <Card key={c.id} className="border" style={{ borderColor: "var(--border)", borderTop: `3px solid ${CORES_CATEGORIA[c.id]}` }}>
              <CardContent className="p-5 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm" style={{ fontWeight: 600 }}>
                    <MarcaCategoria id={c.id} /> {c.nome}
                  </span>
                  <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    {formatarPercentual(c.participacao)} do total
                  </span>
                </div>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  {c.descricao}
                </p>
                <div className="flex items-end justify-between mt-1">
                  <div>
                    <p className="text-2xl" style={{ fontWeight: 700, lineHeight: 1 }}>
                      {formatarNumero(c.prev)}
                    </p>
                    <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                      previstos em {HORIZONTE_DIAS} dias
                    </p>
                  </div>
                  <p className="text-xs text-right" style={{ color: "var(--muted-foreground)" }}>
                    últimos 14 dias: {formatarNumero(c.real)}
                    <br />
                    <span style={{ color: "var(--foreground)", fontWeight: 600 }}>
                      {delta >= 0 ? "▲" : "▼"} {formatarPercentual(Math.abs(delta))}
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Produtos */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-2 pt-5 px-5 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Produtos com maior venda prevista
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Próximos {HORIZONTE_DIAS} dias · {lojas.map((l) => l.nome).join(" + ")}
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => navigate("/previsao")}>
            Ver todos <ArrowRight size={13} />
          </Button>
        </CardHeader>
        <CardContent className="px-0 pb-2">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5">Produto</TableHead>
                <TableHead className="text-xs">Categoria</TableHead>
                <TableHead className="text-xs text-right">Vendido (8 sem.)</TableHead>
                <TableHead className="text-xs">Últimas 8 semanas</TableHead>
                <TableHead className="text-xs text-right pr-5">Previsto ({HORIZONTE_DIAS} dias)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topProdutos.map((p) => (
                <TableRow key={p.codigo}>
                  <TableCell className="text-xs pl-5">
                    <span style={{ fontWeight: 500 }}>{p.nome}</span>
                    <span className="ml-2" style={{ color: "var(--muted-foreground)" }}>
                      cód. {p.codigo}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs">
                    <span className="inline-flex items-center gap-1.5">
                      <MarcaCategoria id={p.categoria} tamanho={8} />
                      {nomeCategoria(p.categoria)}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-right">{formatarQtd(p.vendido_8_semanas)}</TableCell>
                  <TableCell>
                    <MiniBarras valores={p.historico_semanal} cor={CORES_CATEGORIA[p.categoria]} />
                  </TableCell>
                  <TableCell className="text-sm text-right pr-5" style={{ fontWeight: 700 }}>
                    {formatarQtd(p.previsao_14d)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
