import { BellOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { ScrollArea } from "@/app/components/ui/scroll-area";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { EstadoVazio } from "@/app/components/feedback/EstadoVazio";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { contarPorUrgencia } from "@/domain/urgencia";
import { pluralizar } from "@/lib/format";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { CartaoAlertaUrgente } from "./components/CartaoAlertaUrgente";
import { IndicadorCard } from "./components/IndicadorCard";
import { useResumoDashboard } from "./hooks";

const SERIES = [
  { chave: "Rosa Vermelha", cor: estiloUrgencia.critico.cor },
  { chave: "Lírio Branco", cor: estiloUrgencia.ok.cor },
  { chave: "Girassol", cor: estiloUrgencia.atencao.cor },
] as const;

export function DashboardPage() {
  const { data, carregando, erro, recarregar } = useResumoDashboard();

  if (carregando) return <TelaCarregando mensagem="Carregando o resumo de hoje…" />;
  if (erro) return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  if (!data) return null;

  const criticos = contarPorUrgencia(data.alertasUrgentes).critico;

  return (
    <div className="p-6 flex flex-col gap-6 h-full">
      <div className="grid grid-cols-4 gap-4">
        {data.indicadores.map((indicador) => (
          <IndicadorCard key={indicador.chave} indicador={indicador} />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
        <Card className="col-span-2 border flex flex-col" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Vendas nas Últimas 8 Semanas — 3 Produtos Mais Vendidos
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-5 pb-5">
            <ResponsiveContainer width="100%" height="100%" minHeight={260}>
              <LineChart data={data.tendencia}>
                <CartesianGrid strokeDasharray="3 3" stroke={cores.borda} />
                <XAxis dataKey="semana" tick={{ fontSize: 11, fill: cores.textoSuave }} />
                <YAxis tick={{ fontSize: 11, fill: cores.textoSuave }} />
                <Tooltip
                  contentStyle={{
                    background: cores.cartao,
                    border: `1px solid ${cores.borda}`,
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {SERIES.map(({ chave, cor }) => (
                  <Line key={chave} type="monotone" dataKey={chave} stroke={cor} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border flex flex-col" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
                Estoque com Urgência
              </CardTitle>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: estiloUrgencia.critico.fundo,
                  color: estiloUrgencia.critico.cor,
                  fontWeight: 600,
                }}
              >
                {pluralizar(criticos, "urgente")}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex-1 px-4 pb-4 overflow-hidden">
            {data.alertasUrgentes.length === 0 ? (
              <EstadoVazio
                icone={BellOff}
                titulo="Nenhum estoque em urgência"
                descricao="Todos os produtos estão acima do mínimo."
              />
            ) : (
              <ScrollArea className="h-full">
                <div className="flex flex-col gap-2">
                  {data.alertasUrgentes.map((alerta) => (
                    <CartaoAlertaUrgente key={alerta.id} alerta={alerta} />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
