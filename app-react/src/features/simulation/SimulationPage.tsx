import { useMemo, useState } from "react";
import { DollarSign, Lightbulb, Package, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Slider } from "@/app/components/ui/slider";
import { Label } from "@/app/components/ui/label";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { formatarNumero, formatarPercentual } from "@/lib/format";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { useSimulacao } from "./hooks";
import { NENHUM_COMPLEMENTO, recomendacao, type NivelSinergia } from "./model";

const TIPOS_PROMOCAO = [
  { valor: "desconto", label: "Desconto direto" },
  { valor: "combo", label: "Compre 2 leve 3" },
  { valor: "frete", label: "Frete grátis" },
  { valor: "brinde", label: "Brinde na compra" },
];

const DURACOES = [7, 14, 30];

const APARENCIA_SINERGIA: Record<NivelSinergia, { label: string; cor: string; fundo: string }> = {
  baixa: { label: "Baixa", cor: estiloUrgencia.atencao.cor, fundo: estiloUrgencia.atencao.fundo },
  media: { label: "Média", cor: "#1a4fa0", fundo: "#e8f0ff" },
  alta: { label: "Alta", cor: estiloUrgencia.ok.cor, fundo: estiloUrgencia.ok.fundo },
};

export function SimulationPage() {
  const [produtoId, setProdutoId] = useState("rosa-vermelha");
  const [tipoPromocao, setTipoPromocao] = useState("desconto");
  const [desconto, setDesconto] = useState(20);
  const [duracaoDias, setDuracaoDias] = useState(7);
  const [complementoId, setComplementoId] = useState(NENHUM_COMPLEMENTO);

  const parametros = useMemo(
    () => ({ descontoPercentual: desconto, complementoId }),
    [desconto, complementoId],
  );
  const { produtos, resultado, carregando, erro, recarregar } = useSimulacao(produtoId, parametros);

  if (erro) return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  if (carregando || !resultado) return <TelaCarregando mensagem="Montando o cenário…" />;

  const nomeComplemento = produtos.find((produto) => produto.id === complementoId)?.nome ?? "";
  const sinergia = resultado.sinergia;
  const aparencia = sinergia ? APARENCIA_SINERGIA[sinergia.nivel] : null;
  const lucroPositivo = resultado.impactoMargem > 0;

  const indicadores = [
    {
      icone: TrendingUp,
      label: "Aumento nas Vendas",
      valor: `+${formatarPercentual(resultado.variacaoRelativa)}`,
      cor: estiloUrgencia.ok.cor,
      fundo: estiloUrgencia.ok.fundo,
    },
    {
      icone: Package,
      label: "Unidades a mais vendidas",
      valor: `+${formatarNumero(resultado.variacaoUnidades)}`,
      cor: estiloUrgencia.ok.cor,
      fundo: estiloUrgencia.ok.fundo,
    },
    {
      icone: DollarSign,
      label: "Lucro estimado extra",
      valor: `R$ ${formatarNumero(resultado.impactoMargem)}`,
      cor: lucroPositivo ? estiloUrgencia.ok.cor : estiloUrgencia.critico.cor,
      fundo: lucroPositivo ? estiloUrgencia.ok.fundo : estiloUrgencia.critico.fundo,
    },
  ];

  return (
    <div className="p-6 flex gap-5 h-full">
      <div className="w-72 flex-shrink-0 flex flex-col gap-4">
        <Card className="border flex-1" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-3 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Configurar Promoção
            </CardTitle>
          </CardHeader>

          <CardContent className="px-5 pb-5 flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs" style={{ color: cores.textoSuave }}>
                Produto
              </Label>
              <Select
                value={produtoId}
                onValueChange={(valor) => {
                  setProdutoId(valor);
                  setComplementoId(NENHUM_COMPLEMENTO);
                }}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {produtos.map((produto) => (
                    <SelectItem key={produto.id} value={produto.id}>
                      {produto.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label className="text-xs" style={{ color: cores.textoSuave }}>
                Tipo de Promoção
              </Label>
              <Select value={tipoPromocao} onValueChange={setTipoPromocao}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPOS_PROMOCAO.map((tipo) => (
                    <SelectItem key={tipo.valor} value={tipo.valor}>
                      {tipo.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs" style={{ color: cores.textoSuave }}>
                  Desconto (%)
                </Label>
                <span
                  className="text-sm px-2 py-0.5 rounded"
                  style={{ background: "var(--accent)", color: cores.primaria, fontWeight: 700 }}
                >
                  {desconto}%
                </span>
              </div>
              <Slider
                value={[desconto]}
                onValueChange={([valor]) => setDesconto(valor ?? desconto)}
                min={5}
                max={50}
                step={5}
                className="w-full"
                aria-label="Percentual de desconto"
              />
              <div className="flex justify-between text-xs" style={{ color: cores.textoSuave }}>
                <span>5%</span>
                <span>50%</span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label className="text-xs" style={{ color: cores.textoSuave }}>
                Duração da promoção
              </Label>
              <Select value={String(duracaoDias)} onValueChange={(valor) => setDuracaoDias(Number(valor))}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DURACOES.map((dias) => (
                    <SelectItem key={dias} value={String(dias)}>
                      {dias} dias
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label className="text-xs" style={{ color: cores.textoSuave }}>
                Produto em conjunto
              </Label>
              <Select value={complementoId} onValueChange={setComplementoId}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NENHUM_COMPLEMENTO}>Sem produto em conjunto</SelectItem>
                  {produtos
                    .filter((produto) => produto.id !== produtoId)
                    .map((produto) => (
                      <SelectItem key={produto.id} value={produto.id}>
                        {produto.nome}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>

              {sinergia && aparencia && (
                <div
                  className="rounded-lg p-3 flex flex-col gap-2.5 mt-0.5"
                  style={{ background: "var(--muted)", border: `1px solid ${cores.borda}` }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: cores.textoSuave }}>
                      Sinergia entre produtos
                    </span>
                    <span
                      className="text-xs px-2 py-0.5 rounded-full font-semibold"
                      style={{ background: aparencia.fundo, color: aparencia.cor }}
                    >
                      {aparencia.label}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: cores.textoSuave }}>
                      Taxa de adesão estimada
                    </span>
                    <span className="text-xs font-semibold" style={{ color: cores.texto }}>
                      ~{Math.round(sinergia.taxaAceitacao * 100)}% dos clientes
                    </span>
                  </div>

                  <div
                    className="w-full rounded-full overflow-hidden"
                    style={{ height: 4, background: cores.borda }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(sinergia.taxaAceitacao * 100)}%`,
                        background: aparencia.cor,
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

      <div className="flex-1 flex flex-col gap-4 min-w-0">
        <div className="grid grid-cols-3 gap-3">
          {indicadores.map(({ icone: Icone, label, valor, cor, fundo }) => (
            <Card key={label} className="border" style={{ borderColor: cores.borda }}>
              <CardContent className="p-4 flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: fundo }}
                >
                  <Icone size={18} color={cor} />
                </div>
                <div>
                  <p className="text-xl" style={{ color: cor, fontWeight: 700, lineHeight: 1 }}>
                    {valor}
                  </p>
                  <p className="text-xs" style={{ color: cores.textoSuave }}>
                    {label}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="border flex-1" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Vendas por dia — sem promoção vs. com promoção
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={resultado.pontos} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke={cores.borda} />
                <XAxis dataKey="dia" tick={{ fontSize: 11, fill: cores.textoSuave }} />
                <YAxis tick={{ fontSize: 11, fill: cores.textoSuave }} />
                <Tooltip
                  contentStyle={{
                    background: cores.cartao,
                    border: `1px solid ${cores.borda}`,
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="semPromo" name="Sem promoção" fill="var(--switch-background)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="comPromo" name="Com promoção" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <div
          className="rounded-lg px-4 py-3 flex items-start gap-3"
          style={{ background: estiloUrgencia.ok.fundo, border: `1px solid ${estiloUrgencia.ok.borda}` }}
        >
          <Lightbulb size={18} color={estiloUrgencia.ok.cor} className="mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs font-semibold mb-0.5" style={{ color: "#1a4a27" }}>
              Recomendação do Sistema
            </p>
            <p className="text-sm" style={{ color: "#2a6b40" }}>
              {recomendacao(resultado, desconto, nomeComplemento)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
