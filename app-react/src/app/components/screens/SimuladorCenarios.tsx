import { useState, useMemo } from "react";
import {
  TrendingUp,
  Package,
  DollarSign,
  Lightbulb,
} from "lucide-react";
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
import { Slider } from "../ui/slider";
import { Label } from "../ui/label";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  dadosSimulacaoBase,
  produtos,
} from "../../data/mockData";

const tiposCenario = [
  { value: "desconto", label: "Desconto direto" },
  { value: "combo", label: "Compre 2 leve 3" },
  { value: "frete", label: "Frete grátis" },
  { value: "brinde", label: "Brinde na compra" },
];

// Synergy table: maps a companion product id to { nivel, taxa, fator }
// Falls back to DEFAULT_SINERGIA for any unlisted pair.
const SINERGIAS_POR_COMPLEMENTO: Record<
  string,
  {
    nivel: string;
    taxa: number;
    fator: number;
    bg: string;
    cor: string;
  }
> = {
  "rosa-branca": {
    nivel: "Baixa",
    taxa: 0.12,
    fator: 0.05,
    bg: "#fff8e1",
    cor: "#b77800",
  },
  girassol: {
    nivel: "Média",
    taxa: 0.22,
    fator: 0.1,
    bg: "#e8f0ff",
    cor: "#1a4fa0",
  },
  lirio: {
    nivel: "Média",
    taxa: 0.2,
    fator: 0.09,
    bg: "#e8f0ff",
    cor: "#1a4fa0",
  },
  orquidea: {
    nivel: "Alta",
    taxa: 0.32,
    fator: 0.16,
    bg: "#e8f5e0",
    cor: "#1a6b3c",
  },
  "buque-misto": {
    nivel: "Alta",
    taxa: 0.35,
    fator: 0.18,
    bg: "#e8f5e0",
    cor: "#1a6b3c",
  },
};

const DEFAULT_SINERGIA = {
  nivel: "Média",
  taxa: 0.2,
  fator: 0.1,
  bg: "#e8f0ff",
  cor: "#1a4fa0",
};

function getSinergia(companionId: string) {
  return (
    SINERGIAS_POR_COMPLEMENTO[companionId] ?? DEFAULT_SINERGIA
  );
}

export function SimuladorCenarios() {
  const [produto, setProduto] = useState("rosa-vermelha");
  const [cenario, setCenario] = useState("desconto");
  const [desconto, setDesconto] = useState([20]);
  const [periodo, setPeriodo] = useState("7");
  const [produtoCasado, setProdutoCasado] = useState("nenhum");

  const sinergia =
    produtoCasado !== "nenhum"
      ? getSinergia(produtoCasado)
      : null;
  const fatorCombo = sinergia?.fator ?? 0;
  const fatorBase = 1 + (desconto[0] / 100) * 1.8 + fatorCombo;

  const chartData = useMemo(
    () =>
      dadosSimulacaoBase.map((d) => ({
        ...d,
        comPromo: Math.round(d.semPromo * fatorBase),
      })),
    [fatorBase],
  );

  const totalSemPromo = chartData.reduce(
    (s, d) => s + d.semPromo,
    0,
  );
  const totalComPromo = chartData.reduce(
    (s, d) => s + d.comPromo,
    0,
  );
  const variacao = totalComPromo - totalSemPromo;
  const variacaoPct = (
    (variacao / totalSemPromo) *
    100
  ).toFixed(1);
  const margemImpacto = (
    variacao * 0.62 -
    totalComPromo * (desconto[0] / 100) * 0.8
  ).toFixed(0);

  const produtoCasadoNome =
    produtos.find((p) => p.id === produtoCasado)?.nome ?? "";

  const recomendacao =
    desconto[0] <= 15
      ? `Desconto de ${desconto[0]}% é moderado — as vendas devem crescer ${variacaoPct}% sem prejudicar muito o lucro.${sinergia ? ` Combinar com ${produtoCasadoNome} pode aumentar o ticket médio com boa aceitação.` : " Boa opção para semanas comuns."}`
      : desconto[0] <= 25
        ? `Desconto de ${desconto[0]}% equilibra bem o aumento de vendas e o lucro.${sinergia ? ` O combo com ${produtoCasadoNome} deve ser aceito por ~${Math.round(sinergia.taxa * 100)}% dos clientes, elevando ainda mais o resultado.` : " Ótimo para datas especiais como Dia das Mães e Natal."}`
        : `Desconto de ${desconto[0]}% vende muito mais, mas o lucro por unidade cai bastante.${sinergia ? ` Adicionar ${produtoCasadoNome} ao combo ajuda a recuperar margem pelo ticket maior.` : " Use apenas em produtos com muito estoque parado ou alta saída."}`;

  return (
    <div className="p-6 flex gap-5 h-full">
      {/* Left panel — controls */}
      <div className="w-72 flex-shrink-0 flex flex-col gap-4">
        <Card
          className="border flex-1"
          style={{ borderColor: "var(--border)" }}
        >
          <CardHeader className="pb-3 pt-5 px-5">
            <CardTitle
              className="text-sm"
              style={{
                color: "var(--foreground)",
                fontWeight: 600,
              }}
            >
              Configurar Promoção
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-5">
            {/* Produto */}
            <div className="flex flex-col gap-1.5">
              <Label
                className="text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                Produto
              </Label>
              <Select
                value={produto}
                onValueChange={(v) => {
                  setProduto(v);
                  setProdutoCasado("nenhum");
                }}
              >
                <SelectTrigger className="h-9 text-sm">
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

            {/* Tipo de promoção */}
            <div className="flex flex-col gap-1.5">
              <Label
                className="text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                Tipo de Promoção
              </Label>
              <Select
                value={cenario}
                onValueChange={setCenario}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {tiposCenario.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Desconto */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Label
                  className="text-xs"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Desconto (%)
                </Label>
                <span
                  className="text-sm px-2 py-0.5 rounded"
                  style={{
                    background: "var(--accent)",
                    color: "var(--primary)",
                    fontWeight: 700,
                  }}
                >
                  {desconto[0]}%
                </span>
              </div>
              <Slider
                value={desconto}
                onValueChange={setDesconto}
                min={5}
                max={50}
                step={5}
                className="w-full"
              />
              <div
                className="flex justify-between text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                <span>5%</span>
                <span>50%</span>
              </div>
            </div>

            {/* Duração */}
            <div className="flex flex-col gap-1.5">
              <Label
                className="text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                Duração da promoção
              </Label>
              <Select
                value={periodo}
                onValueChange={setPeriodo}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 dias</SelectItem>
                  <SelectItem value="14">14 dias</SelectItem>
                  <SelectItem value="30">30 dias</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* ——— Venda casada ——— */}
            <div className="flex flex-col gap-2">
              <Label
                className="text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                Produto em conjunto
              </Label>
              <Select
                value={produtoCasado}
                onValueChange={setProdutoCasado}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="nenhum">
                    Sem produto em conjunto
                  </SelectItem>
                  {produtos
                    .filter((p) => p.id !== produto)
                    .map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.nome}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>

              {/* Synergy card — only when a companion is selected */}
              {sinergia && (
                <div
                  className="rounded-lg p-3 flex flex-col gap-2.5 mt-0.5"
                  style={{
                    background: "var(--muted)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs"
                      style={{
                        color: "var(--muted-foreground)",
                      }}
                    >
                      Sinergia entre produtos
                    </span>
                    <span
                      className="text-xs px-2 py-0.5 rounded-full font-semibold"
                      style={{
                        background: sinergia.bg,
                        color: sinergia.cor,
                      }}
                    >
                      {sinergia.nivel}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs"
                      style={{
                        color: "var(--muted-foreground)",
                      }}
                    >
                      Taxa de adesão estimada
                    </span>
                    <span
                      className="text-xs font-semibold"
                      style={{ color: "var(--foreground)" }}
                    >
                      ~{Math.round(sinergia.taxa * 100)}% dos
                      clientes
                    </span>
                  </div>

                  {/* Take-rate bar */}
                  <div
                    className="w-full rounded-full overflow-hidden"
                    style={{
                      height: 4,
                      background: "var(--border)",
                    }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(sinergia.taxa * 100)}%`,
                        background: sinergia.cor,
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Impact KPIs */}
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              icon: <TrendingUp size={18} color="#1a6b3c" />,
              label: "Aumento nas Vendas",
              value: `+${variacaoPct}%`,
              bg: "#e8f5e0",
              color: "#1a6b3c",
            },
            {
              icon: <Package size={18} color="#1a6b3c" />,
              label: "Unidades a mais vendidas",
              value: `+${variacao}`,
              bg: "#e8f5e0",
              color: "#1a6b3c",
            },
            {
              icon: (
                <DollarSign
                  size={18}
                  color={
                    Number(margemImpacto) > 0
                      ? "#1a6b3c"
                      : "#d4183d"
                  }
                />
              ),
              label: "Lucro estimado extra",
              value: `R$ ${Number(margemImpacto).toLocaleString("pt-BR")}`,
              bg:
                Number(margemImpacto) > 0
                  ? "#e8f5e0"
                  : "#fff0f3",
              color:
                Number(margemImpacto) > 0
                  ? "#1a6b3c"
                  : "#d4183d",
            },
          ].map((item) => (
            <Card
              key={item.label}
              className="border"
              style={{ borderColor: "var(--border)" }}
            >
              <CardContent className="p-4 flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: item.bg }}
                >
                  {item.icon}
                </div>
                <div>
                  <p
                    className="text-xl"
                    style={{
                      color: item.color,
                      fontWeight: 700,
                      lineHeight: 1,
                    }}
                  >
                    {item.value}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    {item.label}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Comparison chart */}
        <Card
          className="border flex-1"
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
              Vendas por dia — sem promoção vs. com promoção
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barGap={4}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                />
                <XAxis
                  dataKey="dia"
                  tick={{
                    fontSize: 11,
                    fill: "var(--muted-foreground)",
                  }}
                />
                <YAxis
                  tick={{
                    fontSize: 11,
                    fill: "var(--muted-foreground)",
                  }}
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
                <Bar
                  dataKey="semPromo"
                  name="Sem promoção"
                  fill="#a3c9ad"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="comPromo"
                  name="Com promoção"
                  fill="#1a6b3c"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recommendation */}
        <div
          className="rounded-lg px-4 py-3 flex items-start gap-3"
          style={{
            background: "#e8f5e0",
            border: "1px solid #b4dbb4",
          }}
        >
          <Lightbulb
            size={18}
            color="#1a6b3c"
            className="mt-0.5 flex-shrink-0"
          />
          <div>
            <p
              className="text-xs font-semibold mb-0.5"
              style={{ color: "#1a4a27" }}
            >
              Recomendação do Sistema
            </p>
            <p className="text-sm" style={{ color: "#2a6b40" }}>
              {recomendacao}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}