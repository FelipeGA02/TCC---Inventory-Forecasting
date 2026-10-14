import { useMemo, useState } from "react";
import { Boxes, Receipt, ShoppingBag, Truck } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { COR_ENCOMENDA, CORES_CATEGORIA, COR_TOTAL, LIMIAR_ENCOMENDA, categorias, dados } from "../../data/mockData";
import { CATEGORIAS_ANALISE, COR_FLORES, analiseDe, type CategoriaAnalise } from "../../data/analises";
import { FiltroLoja, Kpi, Segmentado, useFiltroLoja } from "../shared";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarMesAno, formatarMoeda, formatarMoedaCompacta, formatarNumero, formatarPercentual } from "@/lib/format";

type Medida = "faturamento" | "volume";
type Ranking = "faturamento" | "volume";

const NOME_CAT: Record<CategoriaAnalise, string> = {
  ...(Object.fromEntries(categorias.map((c) => [c.id, c.nome])) as Record<string, string>),
  "flores-de-corte": "Flores de corte",
} as Record<CategoriaAnalise, string>;
const COR_CAT: Record<CategoriaAnalise, string> = { ...CORES_CATEGORIA, "flores-de-corte": COR_FLORES };

function Legenda({ itens }: { itens: { cor: string; nome: string }[] }) {
  return (
    <div className="flex items-center gap-4 flex-wrap text-xs" style={{ color: "var(--muted-foreground)" }}>
      {itens.map((i) => (
        <span key={i.nome} className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: i.cor }} /> {i.nome}
        </span>
      ))}
    </div>
  );
}

/** Barra horizontal de participação (0–100%), com rótulo e valor. */
function BarraParticipacao({ nome, cor, fracao, valor }: { nome: string; cor: string; fracao: number; valor: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: cor }} /> {nome}
        </span>
        <span>
          <strong>{formatarPercentual(fracao)}</strong> <span style={{ color: "var(--muted-foreground)" }}>· {valor}</span>
        </span>
      </div>
      <div className="h-2 rounded-full" style={{ background: "var(--muted)" }}>
        <div className="h-2 rounded-full" style={{ width: `${Math.max(0, fracao) * 100}%`, background: cor }} />
      </div>
    </div>
  );
}

export function Dashboard() {
  const { unidade } = useFiltroLoja();
  const [medida, setMedida] = useState<Medida>("faturamento");
  const [ranking, setRanking] = useState<Ranking>("faturamento");
  const a = useMemo(() => analiseDe(unidade), [unidade]);
  const r = a.resumo;
  const ticket = r.faturamento / r.notas;

  const mensal = a.mensal.map((m) => ({
    mes: m.mes,
    dia_a_dia: medida === "faturamento" ? m.faturamento - m.faturamento_encomendas : m.volume - m.volume_encomendas,
    encomendas: medida === "faturamento" ? m.faturamento_encomendas : m.volume_encomendas,
    ticket: m.faturamento / Math.max(1, m.notas),
  }));
  const fmtMedida = (v: number) => (medida === "faturamento" ? formatarMoedaCompacta(v) : formatarNumero(v));
  const dias = a.dia_semana.filter((d) => !d.fechado);
  const totalCatVol = CATEGORIAS_ANALISE.reduce((s, c) => s + a.categorias[c].volume, 0);
  const totalCatFat = CATEGORIAS_ANALISE.reduce((s, c) => s + a.categorias[c].faturamento, 0);
  const tc = a.tipo_cliente;
  const totalPag = a.pagamento.reduce((s, p) => s + p.faturamento, 0);
  const top = ranking === "faturamento" ? a.top_faturamento : a.top_volume;

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <FiltroLoja />
        <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          Base de vendas de <strong>{formatarData(a.periodo.inicio)}</strong> a <strong>{formatarData(a.periodo.fim)}</strong> · fretes e serviços fora
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Kpi icone={Receipt} rotulo="Faturamento líquido" valor={formatarMoedaCompacta(r.faturamento)} detalhe={`${formatarMoeda(r.faturamento)} no período, já com descontos`} />
        <Kpi icone={ShoppingBag} rotulo="Notas de venda" valor={formatarNumero(r.notas)} detalhe={`Ticket médio de ${formatarMoeda(ticket)} por nota`} />
        <Kpi icone={Boxes} rotulo="Quantidade vendida" valor={formatarNumero(r.volume)} detalhe={`${formatarNumero(unidade === "todas" ? dados.base.skus : r.produtos)} produtos diferentes · m², bandeja, saco, unidade`} />
        <Kpi
          icone={Truck}
          rotulo="Encomendas"
          valor={`${formatarNumero(r.encomendas.notas)} notas`}
          detalhe={`Acima de ${formatarNumero(LIMIAR_ENCOMENDA)} un. · ${formatarPercentual(r.encomendas.volume / r.volume)} da quantidade e ${formatarPercentual(r.encomendas.faturamento / r.faturamento)} do faturamento`}
        />
      </div>

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-1 pt-5 px-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                {medida === "faturamento" ? "Faturamento" : "Quantidade vendida"} por mês
              </CardTitle>
              <div className="mt-1">
                <Legenda itens={[{ cor: COR_TOTAL, nome: "Venda do dia a dia" }, { cor: COR_ENCOMENDA, nome: "Encomendas" }]} />
              </div>
            </div>
            <Segmentado
              rotulo="Mostrar"
              opcoes={[
                { valor: "faturamento" as Medida, label: "Faturamento" },
                { valor: "volume" as Medida, label: "Quantidade" },
              ]}
              valor={medida}
              onChange={setMedida}
            />
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-4">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={mensal} barCategoryGap="18%">
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="mes" tickFormatter={formatarMesAno} tick={eixo} tickLine={false} axisLine={false} interval={1} />
              <YAxis tick={eixo} tickFormatter={fmtMedida} width={88} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={estiloTooltip}
                cursor={{ fill: "rgba(26,107,60,0.06)" }}
                labelFormatter={(m: string) => formatarMesAno(m)}
                formatter={(v: number, nome: string) => [
                  medida === "faturamento" ? formatarMoeda(v) : formatarNumero(v),
                  nome === "dia_a_dia" ? "Venda do dia a dia" : "Encomendas",
                ]}
              />
              <Bar dataKey="dia_a_dia" stackId="m" fill={COR_TOTAL} stroke="#fff" strokeWidth={1} isAnimationActive={false} />
              <Bar dataKey="encomendas" stackId="m" fill={COR_ENCOMENDA} stroke="#fff" strokeWidth={1} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-1 pt-5 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Faturamento médio por dia da semana
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Último ano, dias de loja aberta, sem encomendas · domingo: loja fechada
            </p>
          </CardHeader>
          <CardContent className="px-3 pb-4">
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={dias} barCategoryGap="28%">
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="dia" tick={eixo} tickLine={false} axisLine={false} />
                <YAxis tick={eixo} tickFormatter={formatarMoedaCompacta} width={88} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={estiloTooltip}
                  cursor={{ fill: "rgba(26,107,60,0.06)" }}
                  formatter={(v: number, _n: string, p) => [
                    `${formatarMoeda(v)} · ${formatarNumero(p.payload.notas_medias)} notas · ${formatarNumero(p.payload.volume_medio)} un.`,
                    "Média do dia",
                  ]}
                />
                <Bar dataKey="faturamento_medio" fill={COR_TOTAL} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Mix por categoria
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Participação na quantidade vendida e no faturamento do período, incluindo encomendas
            </p>
          </CardHeader>
          <CardContent className="px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div className="flex flex-col gap-3">
              <p className="text-xs" style={{ fontWeight: 600 }}>Quantidade</p>
              {CATEGORIAS_ANALISE.map((c) => (
                <BarraParticipacao key={c} nome={NOME_CAT[c]} cor={COR_CAT[c]} fracao={a.categorias[c].volume / totalCatVol} valor={formatarNumero(a.categorias[c].volume)} />
              ))}
            </div>
            <div className="flex flex-col gap-3">
              <p className="text-xs" style={{ fontWeight: 600 }}>Faturamento</p>
              {CATEGORIAS_ANALISE.map((c) => (
                <BarraParticipacao key={c} nome={NOME_CAT[c]} cor={COR_CAT[c]} fracao={a.categorias[c].faturamento / totalCatFat} valor={formatarMoedaCompacta(a.categorias[c].faturamento)} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Consumidor × cliente cadastrado
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Cliente cadastrado inclui empresas e obras que compram no balcão · nenhum dado pessoal é exibido
            </p>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-4">
            {(
              [
                ["Notas", tc.consumidor.notas, tc.cadastrado.notas, formatarNumero],
                ["Quantidade", tc.consumidor.volume, tc.cadastrado.volume, formatarNumero],
                ["Faturamento", tc.consumidor.faturamento, tc.cadastrado.faturamento, formatarMoedaCompacta],
              ] as [string, number, number, (v: number) => string][]
            ).map(([rot, cons, cad, fmt]) => {
              const tot = cons + cad;
              return (
                <div key={rot} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ fontWeight: 600 }}>{rot}</span>
                    <span style={{ color: "var(--muted-foreground)" }}>
                      consumidor {fmt(cons)} · cadastrado {fmt(cad)}
                    </span>
                  </div>
                  <div className="flex h-3 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
                    <div style={{ width: `${(cons / tot) * 100}%`, background: "#3a6ea5" }} title={`Consumidor: ${formatarPercentual(cons / tot)}`} />
                    <div style={{ width: `${(cad / tot) * 100}%`, background: "#c8650f" }} title={`Cadastrado: ${formatarPercentual(cad / tot)}`} />
                  </div>
                  <div className="flex justify-between text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                    <span>{formatarPercentual(cons / tot)}</span>
                    <span>{formatarPercentual(cad / tot)}</span>
                  </div>
                </div>
              );
            })}
            <Legenda itens={[{ cor: "#3a6ea5", nome: "Consumidor (balcão)" }, { cor: "#c8650f", nome: "Cliente cadastrado" }]} />
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              Ticket médio: consumidor {formatarMoeda(tc.consumidor.faturamento / tc.consumidor.notas)} · cadastrado{" "}
              {formatarMoeda(tc.cadastrado.faturamento / tc.cadastrado.notas)}
            </p>
          </CardContent>
        </Card>

        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Formas de pagamento
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Participação no faturamento do período
            </p>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-3">
            {a.pagamento.map((p) => (
              <BarraParticipacao key={p.forma} nome={p.forma} cor={COR_TOTAL} fracao={p.faturamento / totalPag} valor={`${formatarMoedaCompacta(p.faturamento)} · ${formatarNumero(p.notas)} notas`} />
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-2 pt-5 px-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                Produtos mais vendidos · último ano
              </CardTitle>
              <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                {formatarData(a.periodo.inicio_ultimo_ano)} a {formatarData(a.periodo.fim)} · inclui encomendas
              </p>
            </div>
            <Segmentado
              rotulo="Ordenar por"
              opcoes={[
                { valor: "faturamento" as Ranking, label: "Faturamento" },
                { valor: "volume" as Ranking, label: "Quantidade" },
              ]}
              valor={ranking}
              onChange={setRanking}
            />
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-2 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5 w-10">#</TableHead>
                <TableHead className="text-xs">Produto</TableHead>
                <TableHead className="text-xs">Categoria</TableHead>
                <TableHead className="text-xs text-right">Quantidade</TableHead>
                <TableHead className="text-xs text-right">Faturamento</TableHead>
                <TableHead className="text-xs text-right pr-5">Notas</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {top.map((p, i) => (
                <TableRow key={p.codigo}>
                  <TableCell className="text-xs pl-5" style={{ color: "var(--muted-foreground)" }}>
                    {i + 1}
                  </TableCell>
                  <TableCell className="text-xs">
                    <span style={{ fontWeight: 500 }}>{p.nome}</span>
                    <span className="ml-2" style={{ color: "var(--muted-foreground)" }}>
                      cód. {p.codigo}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="inline-block w-2 h-2 rounded-sm" style={{ background: COR_CAT[p.categoria] }} /> {NOME_CAT[p.categoria]}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-right" style={{ fontWeight: ranking === "volume" ? 700 : 400 }}>
                    {formatarNumero(p.volume)}
                  </TableCell>
                  <TableCell className="text-xs text-right" style={{ fontWeight: ranking === "faturamento" ? 700 : 400 }}>
                    {formatarMoeda(p.faturamento)}
                  </TableCell>
                  <TableCell className="text-xs text-right pr-5">{formatarNumero(p.notas)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
