import { Brain, Package, Clock, ArrowDownRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { tendenciaProdutos } from "../../data/mockData";

const kpis = [
  {
    label: "Precisão das Previsões (MAPE)",
    value: "7.4%",
    sub: "↓ melhorou vs. semana ant.",
    trend: "down",
    icon: Brain,
    color: "#1a6b3c",
    bg: "#e8f5e0",
    tooltip: "MAPE: quanto as previsões erram em média. Quanto menor, melhor.",
  },
  {
    label: "Produtos Monitorados",
    value: "142",
    sub: "7 tipos, 2 lojas",
    trend: "neutral",
    icon: Package,
    color: "#1a6b3c",
    bg: "#e8f5e0",
  },
  {
    label: "Próximo Cálculo Automático",
    value: "2h 18m",
    sub: "Sab, 24 Jun 08:00",
    trend: "neutral",
    icon: Clock,
    color: "#f0a500",
    bg: "#fff8e1",
  },
];

export function Dashboard() {
  return (
    <div className="p-6 flex flex-col gap-6 h-full">
      {/* KPI Grid */}
      <div className="grid grid-cols-3 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="border" style={{ borderColor: "var(--border)" }}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ background: kpi.bg }}
                  >
                    <Icon size={20} color={kpi.color} />
                  </div>
                  {kpi.trend === "down" && (
                    <span className="flex items-center gap-0.5 text-xs" style={{ color: "#1a6b3c" }}>
                      <ArrowDownRight size={13} /> <span>{kpi.sub}</span>
                    </span>
                  )}
                </div>
                <p className="text-3xl mb-0.5" style={{ color: "var(--foreground)", fontWeight: 700, lineHeight: 1 }}>
                  {kpi.value}
                </p>
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  {kpi.label}
                </p>
                {kpi.trend === "neutral" && (
                  <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                    {kpi.sub}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Trend Chart */}
      <div className="flex-1 min-h-0">
        <Card className="h-full border flex flex-col" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
              Vendas nas Últimas 8 Semanas — 3 Produtos Mais Vendidos
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-5 pb-5">
            <ResponsiveContainer width="100%" height="100%" minHeight={260}>
              <LineChart data={tendenciaProdutos}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="semana" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                <Tooltip
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line id="line-rosa" type="monotone" dataKey="Rosa Vermelha" stroke="#d4183d" strokeWidth={2} dot={false} />
                <Line id="line-lirio" type="monotone" dataKey="Lírio Branco" stroke="#1a6b3c" strokeWidth={2} dot={false} />
                <Line id="line-girassol" type="monotone" dataKey="Girassol" stroke="#f0a500" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
