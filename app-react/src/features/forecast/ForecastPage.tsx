import { useMemo, useState } from "react";
import { CalendarDays } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { formatarNumero } from "@/lib/format";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { useCatalogo, usePrevisao } from "./hooks";

const HORIZONTES = [2, 4, 6, 8];

const SEMANA_ATUAL = "Atual";

export function ForecastPage() {
  const [produtoId, setProdutoId] = useState("rosa-vermelha");
  const [unidadeId, setUnidadeId] = useState("centro");
  const [horizonte, setHorizonte] = useState(4);

  const catalogo = useCatalogo();
  const parametros = useMemo(
    () => ({ produtoId, unidadeId, horizonte }),
    [produtoId, unidadeId, horizonte],
  );
  const { data, carregando, erro, recarregar } = usePrevisao(parametros);

  const dadosGrafico = useMemo(
    () =>
      (data?.serie ?? []).map((ponto) => ({
        ...ponto,
        intervalo: ponto.inf !== null && ponto.sup !== null ? [ponto.inf, ponto.sup] : undefined,
      })),
    [data?.serie],
  );

  const totalRecomendado = (data?.recomendacaoSemanal ?? []).reduce(
    (soma, linha) => soma + linha.recomendada,
    0,
  );

  return (
    <div className="p-6 flex flex-col gap-5">
      <Card className="border" style={{ borderColor: cores.borda }}>
        <CardContent className="p-4 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium" style={{ color: cores.textoSuave }}>
              Produto
            </span>
            <Select value={produtoId} onValueChange={setProdutoId}>
              <SelectTrigger className="h-8 text-xs w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(catalogo.data?.produtos ?? []).map((produto) => (
                  <SelectItem key={produto.id} value={produto.id}>
                    {produto.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium" style={{ color: cores.textoSuave }}>
              Unidade
            </span>
            <Select value={unidadeId} onValueChange={setUnidadeId}>
              <SelectTrigger className="h-8 text-xs w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(catalogo.data?.unidades ?? []).map((unidade) => (
                  <SelectItem key={unidade.id} value={unidade.id}>
                    {unidade.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium" style={{ color: cores.textoSuave }}>
              Prever para
            </span>
            <Select value={String(horizonte)} onValueChange={(valor) => setHorizonte(Number(valor))}>
              <SelectTrigger className="h-8 text-xs w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {HORIZONTES.map((semanas) => (
                  <SelectItem key={semanas} value={String(semanas)}>
                    próximas {semanas} semanas
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {erro ? (
        <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />
      ) : carregando || !data ? (
        <TelaCarregando mensagem="Calculando a previsão…" />
      ) : (
        <>
          <div className="grid grid-cols-4 gap-3">
            {data.metricas.map((metrica) => (
              <Card key={metrica.sigla} className="border" style={{ borderColor: cores.borda }}>
                <CardContent className="p-4">
                  <p className="text-xs mb-1" style={{ color: cores.textoSuave }}>
                    {metrica.explicacao}
                  </p>
                  <p className="text-2xl" style={{ color: cores.primaria, fontWeight: 700, lineHeight: 1 }}>
                    {metrica.valor}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: cores.textoSuave, fontWeight: 600 }}>
                    {metrica.sigla}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          {data.eventos.map((evento) => (
            <div
              key={evento.semana}
              className="rounded-lg px-4 py-2.5 flex items-center gap-2 text-sm"
              style={{
                background: estiloUrgencia.atencao.fundo,
                border: `1px solid ${estiloUrgencia.atencao.borda}`,
              }}
            >
              <CalendarDays size={16} color={estiloUrgencia.atencao.cor} />
              <span style={{ color: estiloUrgencia.atencao.cor, fontWeight: 500 }}>
                Atenção: <strong>{evento.nome}</strong> na {evento.semana} — as vendas tendem a ser cerca de{" "}
                {Math.round(evento.impactoEsperado * 100)}% maiores que o normal nessa data.
              </span>
            </div>
          ))}

          <div className="grid grid-cols-3 gap-4">
            <Card className="col-span-2 border flex flex-col" style={{ borderColor: cores.borda }}>
              <CardHeader className="pb-2 pt-4 px-5">
                <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
                  Vendas passadas + estimativa futura (área sombreada = margem de variação)
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 px-4 pb-5">
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={dadosGrafico}>
                    <CartesianGrid strokeDasharray="3 3" stroke={cores.borda} />
                    <XAxis dataKey="semana" tick={{ fontSize: 10, fill: cores.textoSuave }} />
                    <YAxis tick={{ fontSize: 10, fill: cores.textoSuave }} />
                    <Tooltip
                      contentStyle={{
                        background: cores.cartao,
                        border: `1px solid ${cores.borda}`,
                        borderRadius: 8,
                        fontSize: 11,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <ReferenceLine
                      x={SEMANA_ATUAL}
                      stroke={cores.borda}
                      strokeDasharray="4 4"
                      label={{ value: "Hoje", fontSize: 10 }}
                    />
                    <Area
                      dataKey="intervalo"
                      fill="var(--chart-3)"
                      fillOpacity={0.35}
                      stroke="none"
                      name="Margem de variação"
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="quantidade"
                      stroke={cores.primaria}
                      strokeWidth={2}
                      dot={{ r: 3, fill: "#1a6b3c", stroke: "#fff", strokeWidth: 1 }}
                      activeDot={{ r: 5 }}
                      name="Quantidade"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="border" style={{ borderColor: cores.borda }}>
              <CardHeader className="pb-2 pt-4 px-5">
                <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
                  Quanto comprar por semana
                </CardTitle>
              </CardHeader>
              <CardContent className="px-0 pb-0">
                <Table>
                  <TableHeader>
                    <TableRow style={{ background: "var(--muted)" }}>
                      <TableHead className="text-xs pl-4">Semana</TableHead>
                      <TableHead className="text-xs text-right">Comprar</TableHead>
                      <TableHead className="text-xs text-right pr-4">Total acum.</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recomendacaoSemanal.map((linha) => (
                      <TableRow key={linha.semana}>
                        <TableCell className="text-xs pl-4" style={{ color: cores.textoSuave }}>
                          {linha.semana}
                        </TableCell>
                        <TableCell
                          className="text-xs text-right"
                          style={{ color: cores.texto, fontWeight: 600 }}
                        >
                          {formatarNumero(linha.recomendada)}
                        </TableCell>
                        <TableCell className="text-xs text-right pr-4" style={{ color: cores.textoSuave }}>
                          {formatarNumero(linha.total)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                <div
                  className="px-4 py-3 border-t flex justify-between"
                  style={{ borderColor: cores.borda }}
                >
                  <span className="text-xs font-medium" style={{ color: cores.textoSuave }}>
                    Total para {horizonte} semanas
                  </span>
                  <span className="text-sm font-bold" style={{ color: cores.primaria }}>
                    {formatarNumero(totalRecomendado)} un.
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
