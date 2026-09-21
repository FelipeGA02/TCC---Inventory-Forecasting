import { useState } from "react";
import { CalendarDays } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  previsaoSarimax,
  tabelaPrevisaoSemanal,
  produtos,
  unidades,
} from "../../data/mockData";

const metricas = [
  {
    label: "MAE",
    value: "31.4",
    desc: "Erro médio em unidades — o sistema erra ~31 un. por semana",
  },
  {
    label: "MAPE",
    value: "7.4%",
    desc: "Precisão geral — quanto menor, mais certo o sistema acerta",
  },
  {
    label: "RMSE",
    value: "38.7",
    desc: "Sensibilidade a erros grandes — penaliza desvios fortes",
  },
  {
    label: "R²",
    value: "0.923",
    desc: "Confiança do modelo — 0.92 = explica 92% das variações de vendas",
  },
];

const datasComemoratvas = [
  { semana: "Sem +1", evento: "Festa Junina", cor: "#f0a500" },
];

export function PrevisaoSarimax() {
  const [produto, setProduto] = useState("rosa-vermelha");
  const [unidade, setUnidade] = useState("jardim-canada");
  const [horizonte, setHorizonte] = useState("4");

  const chartData = previsaoSarimax.map((d) => ({
    ...d,
    intervalo:
      d.inf !== null && d.sup !== null
        ? [d.inf, d.sup]
        : undefined,
  }));

  const eventoSemana = datasComemoratvas.find(
    (e) => e.semana === "Sem +1",
  );

  return (
    <div className="p-6 flex flex-col gap-5">
      {/* Filters */}
      <Card
        className="border"
        style={{ borderColor: "var(--border)" }}
      >
        <CardContent className="p-4 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-medium"
              style={{ color: "var(--muted-foreground)" }}
            >
              Produto
            </span>

            <Select value={produto} onValueChange={setProduto}>
              <SelectTrigger className="h-8 text-xs w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {produtos.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-medium"
              style={{ color: "var(--muted-foreground)" }}
            >
              Unidade
            </span>
            <Select value={unidade} onValueChange={setUnidade}>
              <SelectTrigger className="h-8 text-xs w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {unidades.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-medium"
              style={{ color: "var(--muted-foreground)" }}
            >
              Prever para
            </span>
            <Select
              value={horizonte}
              onValueChange={setHorizonte}
            >
              <SelectTrigger className="h-8 text-xs w-42">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["2", "4", "6", "8"].map((h) => (
                  <SelectItem key={h} value={h}>
                    próximas {h} semanas
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-3">
        {metricas.map((m) => (
          <Card
            key={m.label}
            className="border"
            style={{ borderColor: "var(--border)" }}
          >
            <CardContent className="p-4">
              <p
                className="text-xs mb-1"
                style={{ color: "var(--muted-foreground)" }}
              >
                {m.desc}
              </p>
              <p
                className="text-2xl"
                style={{
                  color: "var(--primary)",
                  fontWeight: 700,
                  lineHeight: 1,
                }}
              >
                {m.value}
              </p>
              <p
                className="text-xs mt-0.5"
                style={{
                  color: "var(--muted-foreground)",
                  fontWeight: 600,
                }}
              >
                {m.label}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Date event alert */}
      {eventoSemana && (
        <div
          className="rounded-lg px-4 py-2.5 flex items-center gap-2 text-sm"
          style={{
            background: "#fff8e1",
            border: "1px solid #ffe0a0",
          }}
        >
          <CalendarDays size={16} color="#b77800" />
          <span style={{ color: "#b77800", fontWeight: 500 }}>
            Atenção: <strong>{eventoSemana.evento}</strong> na{" "}
            {eventoSemana.semana} — as vendas tendem a ser ~35%
            maiores que o normal nessa data.
          </span>
        </div>
      )}

      {/* Chart + Table */}
      <div className="grid grid-cols-3 gap-4">
        <Card
          className="col-span-2 border flex flex-col"
          style={{ borderColor: "var(--border)" }}
        >
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle
              className="text-sm"
              style={{
                color: "var(--foreground)",
                fontWeight: 600,
              }}
            >
              Vendas passadas + estimativa futura (área
              sombreada = margem de variação)
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-4 pb-5">
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                />
                <XAxis
                  dataKey="semana"
                  tick={{
                    fontSize: 10,
                    fill: "var(--muted-foreground)",
                  }}
                />
                <YAxis
                  tick={{
                    fontSize: 10,
                    fill: "var(--muted-foreground)",
                  }}
                  domain={[200, 650]}
                />
                <Tooltip
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <ReferenceLine
                  x="Atual"
                  stroke="var(--border)"
                  strokeDasharray="4 4"
                  label={{ value: "Hoje", fontSize: 10 }}
                />
                <Area
                  id="area-intervalo"
                  dataKey="intervalo"
                  fill="#c8e6c9"
                  stroke="none"
                  name="Intervalo de Confiança"
                  connectNulls
                />
                <Line
                  id="line-quantidade"
                  type="monotone"
                  dataKey="quantidade"
                  stroke="#1a6b3c"
                  strokeWidth={2}
                  dot={{
                    r: 3,
                    fill: "#1a6b3c",
                    stroke: "#fff",
                    strokeWidth: 1,
                  }}
                  activeDot={{ r: 5 }}
                  name="Quantidade"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Weekly Table */}
        <Card
          className="border"
          style={{ borderColor: "var(--border)" }}
        >
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle
              className="text-sm"
              style={{
                color: "var(--foreground)",
                fontWeight: 600,
              }}
            >
              Quanto comprar por semana
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <Table>
              <TableHeader>
                <TableRow
                  style={{ background: "var(--muted)" }}
                >
                  <TableHead className="text-xs pl-4">
                    Semana
                  </TableHead>
                  <TableHead className="text-xs text-right">
                    Comprar
                  </TableHead>
                  <TableHead className="text-xs text-right pr-4">
                    Total acum.
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tabelaPrevisaoSemanal.map((row, i) => (
                  <TableRow key={i}>
                    <TableCell
                      className="text-xs pl-4"
                      style={{
                        color: "var(--muted-foreground)",
                      }}
                    >
                      {row.semana}
                    </TableCell>
                    <TableCell
                      className="text-xs text-right"
                      style={{
                        color: "var(--foreground)",
                        fontWeight: 600,
                      }}
                    >
                      {row.recomendada}
                    </TableCell>
                    <TableCell
                      className="text-xs text-right pr-4"
                      style={{
                        color: "var(--muted-foreground)",
                      }}
                    >
                      {row.total}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div
              className="px-4 py-3 border-t flex justify-between"
              style={{ borderColor: "var(--border)" }}
            >
              <span
                className="text-xs font-medium"
                style={{ color: "var(--muted-foreground)" }}
              >
                Total para 4 semanas
              </span>
              <span
                className="text-sm font-bold"
                style={{ color: "var(--primary)" }}
              >
                {tabelaPrevisaoSemanal.reduce(
                  (s, r) => s + r.recomendada,
                  0,
                )}{" "}
                un.
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}