import { useMemo, useState } from "react";
import { CalendarDays, Info, Search } from "lucide-react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import type { CategoriaId } from "@/domain/types";
import {
  CORES_CATEGORIA,
  HORIZONTE_DIAS,
  categorias,
  historicoDiarioDe,
  nomeCategoria,
  previsaoDe,
  produtosDe,
  somar,
  unidadesDoFiltro,
} from "../../data/mockData";
import { FiltroLoja, MarcaCategoria, MiniBarras, Segmentado, StatusBadge, useFiltroLoja } from "../shared";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDiaMes, formatarNumero, formatarPercentual, formatarQtd } from "@/lib/format";

type Nivel = "total" | CategoriaId;
const DIAS_HISTORICO_GRAFICO = 28;
const COR_TOTAL = "#1a6b3c";

const opcoesNivel: { valor: Nivel; label: string }[] = [
  { valor: "total", label: "Loja inteira" },
  ...categorias.map((c) => ({ valor: c.id as Nivel, label: c.nome })),
];

export function PrevisaoSarimax() {
  const { unidade } = useFiltroLoja();
  const [nivel, setNivel] = useState<Nivel>("total");
  const [categoriaProdutos, setCategoriaProdutos] = useState<CategoriaId>("grama");
  const [busca, setBusca] = useState("");
  const [produtoSel, setProdutoSel] = useState<string | null>(null);

  const previsao = useMemo(() => previsaoDe(unidade), [unidade]);
  const historico = useMemo(() => historicoDiarioDe(unidade).slice(-DIAS_HISTORICO_GRAFICO), [unidade]);
  const lojas = unidadesDoFiltro(unidade);
  const cor = nivel === "total" ? COR_TOTAL : CORES_CATEGORIA[nivel];

  const faixaDe = (d: (typeof previsao)[number]) => (nivel === "total" ? d : d.categorias[nivel]);

  const grafico = useMemo(() => {
    const hist = historico.map((d) => ({
      data: d.data,
      real: nivel === "total" ? d.total : d.categorias[nivel],
    }));
    const ultimo = hist[hist.length - 1]!;
    const prev = previsao.map((d) => {
      const f = nivel === "total" ? d : d.categorias[nivel];
      return { data: d.data, previsto: f.previsto, faixa: [f.inf, f.sup] as [number, number], evento: d.evento, fechada: d.loja_fechada };
    });
    // O último dia real também abre a linha da previsão, para as duas se tocarem.
    return [...hist.slice(0, -1), { ...ultimo, previsto: ultimo.real }, ...prev];
  }, [historico, previsao, nivel]);

  const total = somar(previsao.map((d) => faixaDe(d).previsto));
  const totalInf = somar(previsao.map((d) => faixaDe(d).inf));
  const totalSup = somar(previsao.map((d) => faixaDe(d).sup));
  const eventos = previsao.filter((d) => d.evento);

  const produtos = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return produtosDe(unidade)
      .filter((p) => p.categoria === categoriaProdutos)
      .filter((p) => !termo || p.nome.toLowerCase().includes(termo) || p.codigo.includes(termo))
      .sort((a, b) => b.previsao_14d - a.previsao_14d);
  }, [unidade, categoriaProdutos, busca]);
  const produto = produtos.find((p) => p.codigo === produtoSel) ?? produtos[0];

  return (
    <div className="p-6 flex flex-col gap-5">
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardContent className="p-4 flex items-center gap-6 flex-wrap">
          <FiltroLoja />
          <Segmentado rotulo="Ver" opcoes={opcoesNivel} valor={nivel} onChange={setNivel} />
        </CardContent>
      </Card>

      {eventos.length > 0 && (
        <div className="rounded-lg px-4 py-2.5 flex items-center gap-2 text-sm" style={{ background: "#fff8e1", border: "1px solid #ffe0a0", color: "#8a5a00" }}>
          <CalendarDays size={16} />
          <span>
            {eventos.map((e) => (
              <span key={e.data}>
                <strong>{e.evento}</strong> em {formatarDiaMes(e.data)} ({e.dia_semana})
                {e.loja_fechada ? " — loja fechada, sem venda prevista." : "."}{" "}
              </span>
            ))}
          </span>
        </div>
      )}

      {/* Gráfico + resumo */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2 border" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-1 pt-4 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              {nivel === "total" ? "Venda da loja" : nomeCategoria(nivel)} · últimos {DIAS_HISTORICO_GRAFICO} dias e próximos {HORIZONTE_DIAS}
            </CardTitle>
            <div className="flex items-center gap-4 text-xs mt-1 flex-wrap" style={{ color: "var(--muted-foreground)" }}>
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: cor }} /> Venda mais provável
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: cor, opacity: 0.18 }} /> Faixa provável (95%)
              </span>
            </div>
          </CardHeader>
          <CardContent className="px-3 pb-4">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={grafico}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={3} />
                <YAxis tick={eixo} tickFormatter={(v: number) => formatarNumero(v)} width={56} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={estiloTooltip}
                  labelFormatter={(d: string) => formatarData(d)}
                  formatter={(v: number | [number, number], nome: string) => {
                    if (nome === "faixa" && Array.isArray(v)) return [`${formatarNumero(v[0])} a ${formatarNumero(v[1])}`, "Faixa provável"];
                    return [formatarNumero(v as number), nome === "real" ? "Vendido" : "Venda mais provável"];
                  }}
                />
                <ReferenceLine x={previsao[0]!.data} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "hoje", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
                <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.18} isAnimationActive={false} />
                <Line dataKey="real" stroke="var(--foreground)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
                <Line dataKey="previsto" stroke={cor} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3, fill: cor, stroke: "#fff", strokeWidth: 1 }} activeDot={{ r: 5 }} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border flex flex-col" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-4 px-5">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Próximos {HORIZONTE_DIAS} dias
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-4">
            <div>
              <p className="text-3xl" style={{ fontWeight: 700, lineHeight: 1, color: cor }}>
                {formatarNumero(total)}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                venda mais provável · faixa de {formatarNumero(totalInf)} a {formatarNumero(totalSup)}
              </p>
            </div>
            {nivel === "total" && (
              <div className="flex flex-col gap-2">
                {categorias.map((c) => {
                  const v = somar(previsao.map((d) => d.categorias[c.id].previsto));
                  return (
                    <div key={c.id} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="inline-flex items-center gap-1.5">
                          <MarcaCategoria id={c.id} /> {c.nome}
                        </span>
                        <span style={{ fontWeight: 600 }}>{formatarNumero(v)}</span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: "var(--muted)" }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${(v / total) * 100}%`, background: CORES_CATEGORIA[c.id] }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="flex flex-col gap-2 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
              {lojas.map((l) => (
                <div key={l.id} className="flex items-center justify-between text-xs">
                  <span>{l.nome}</span>
                  <StatusBadge status={l.modelo.status} compacto />
                </div>
              ))}
              <p className="text-xs flex gap-1.5" style={{ color: "var(--muted-foreground)" }}>
                <Info size={13} className="flex-shrink-0 mt-0.5" />
                A venda mais provável é o valor do meio: metade dos dias vende mais, metade menos. Para ter
                produto disponível, olhe também o limite de cima da faixa.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabela diária */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            Dia a dia
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-2 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5">Data</TableHead>
                <TableHead className="text-xs">Dia</TableHead>
                {nivel === "total" &&
                  categorias.map((c) => (
                    <TableHead key={c.id} className="text-xs text-right">
                      {c.nome}
                    </TableHead>
                  ))}
                <TableHead className="text-xs text-right">Venda mais provável</TableHead>
                <TableHead className="text-xs text-right">Faixa provável</TableHead>
                <TableHead className="text-xs pr-5">Observação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {previsao.map((d) => {
                const f = faixaDe(d);
                return (
                  <TableRow key={d.data} style={d.loja_fechada ? { color: "var(--muted-foreground)" } : undefined}>
                    <TableCell className="text-xs pl-5">{formatarDiaMes(d.data)}</TableCell>
                    <TableCell className="text-xs">{d.dia_semana}</TableCell>
                    {nivel === "total" &&
                      categorias.map((c) => (
                        <TableCell key={c.id} className="text-xs text-right">
                          {formatarNumero(d.categorias[c.id].previsto)}
                        </TableCell>
                      ))}
                    <TableCell className="text-xs text-right" style={{ fontWeight: 700 }}>
                      {formatarNumero(f.previsto)}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {formatarNumero(f.inf)} – {formatarNumero(f.sup)}
                    </TableCell>
                    <TableCell className="text-xs pr-5">
                      {d.loja_fechada ? "Loja fechada" : ""}
                      {d.evento ? ` · ${d.evento}` : ""}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Produtos */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-4 px-5 flex flex-col gap-3">
          <div>
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Previsão por produto
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Os 10 produtos que mais venderam em cada categoria nas últimas 8 semanas. A previsão da categoria é repartida
              pela participação de cada produto nesse período.
            </p>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <Segmentado
              rotulo="Categoria"
              opcoes={categorias.map((c) => ({ valor: c.id, label: c.nome }))}
              valor={categoriaProdutos}
              onChange={(c) => {
                setCategoriaProdutos(c);
                setProdutoSel(null);
              }}
            />
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
              <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar produto ou código" className="h-8 text-xs pl-8 w-56" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-0 grid grid-cols-1 xl:grid-cols-5">
          <div className="xl:col-span-3 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow style={{ background: "var(--muted)" }}>
                  <TableHead className="text-xs pl-5">Produto</TableHead>
                  <TableHead className="text-xs">Tipo</TableHead>
                  <TableHead className="text-xs text-right">Parte da categoria</TableHead>
                  <TableHead className="text-xs">8 semanas</TableHead>
                  <TableHead className="text-xs text-right pr-5">Previsto {HORIZONTE_DIAS} dias</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {produtos.map((p) => {
                  const ativo = produto?.codigo === p.codigo;
                  return (
                    <TableRow
                      key={p.codigo}
                      onClick={() => setProdutoSel(p.codigo)}
                      className="cursor-pointer"
                      style={{ background: ativo ? "var(--secondary)" : undefined }}
                    >
                      <TableCell className="text-xs pl-5">
                        <p style={{ fontWeight: 500 }}>{p.nome}</p>
                        <p style={{ color: "var(--muted-foreground)" }}>cód. {p.codigo}</p>
                      </TableCell>
                      <TableCell className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                        {p.subcategoria}
                      </TableCell>
                      <TableCell className="text-xs text-right">{formatarPercentual(p.participacao_categoria)}</TableCell>
                      <TableCell>
                        <MiniBarras valores={p.historico_semanal} cor={CORES_CATEGORIA[p.categoria]} />
                      </TableCell>
                      <TableCell className="text-sm text-right pr-5" style={{ fontWeight: 700 }}>
                        {formatarQtd(p.previsao_14d)}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {produtos.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-xs text-center py-8" style={{ color: "var(--muted-foreground)" }}>
                      Nenhum produto encontrado.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="xl:col-span-2 border-t xl:border-t-0 xl:border-l p-5 flex flex-col gap-3" style={{ borderColor: "var(--border)" }}>
            {produto ? (
              <>
                <div>
                  <p className="text-sm" style={{ fontWeight: 600 }}>
                    {produto.nome}
                  </p>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    cód. {produto.codigo} · {produto.subcategoria} · vendido em {formatarNumero(produto.dias_com_venda)} dias desde
                    jan/2024
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                    <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Vendido (8 semanas)</p>
                    <p className="text-lg" style={{ fontWeight: 700 }}>{formatarQtd(produto.vendido_8_semanas)}</p>
                  </div>
                  <div className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                    <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Previsto ({HORIZONTE_DIAS} dias)</p>
                    <p className="text-lg" style={{ fontWeight: 700, color: CORES_CATEGORIA[produto.categoria] }}>
                      {formatarQtd(produto.previsao_14d)}
                    </p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <ComposedChart data={produto.previsao.map((d) => ({ ...d, faixa: [d.inf, d.sup] }))}>
                    <CartesianGrid vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={2} />
                    <YAxis tick={eixo} width={44} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
                    <Tooltip
                      contentStyle={estiloTooltip}
                      labelFormatter={(d: string) => formatarData(d)}
                      formatter={(v: number | [number, number], nome: string) =>
                        nome === "faixa" && Array.isArray(v)
                          ? [`${formatarQtd(v[0])} a ${formatarQtd(v[1])}`, "Faixa provável"]
                          : [formatarQtd(v as number), "Venda mais provável"]
                      }
                    />
                    <Area dataKey="faixa" stroke="none" fill={CORES_CATEGORIA[produto.categoria]} fillOpacity={0.15} isAnimationActive={false} />
                    <Bar dataKey="previsto" fill={CORES_CATEGORIA[produto.categoria]} radius={[4, 4, 0, 0]} barSize={12} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  Fatia de {formatarPercentual(produto.participacao_categoria)} da previsão de {nomeCategoria(produto.categoria)}, com o
                  mesmo perfil de dia da semana da categoria.
                </p>
              </>
            ) : (
              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                Selecione um produto para ver a previsão diária.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
