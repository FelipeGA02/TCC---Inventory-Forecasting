import { useMemo, useState } from "react";
import { CalendarDays, CheckCircle2, Info, Scale, Search, Target, TrendingUp, type LucideIcon } from "lucide-react";
import { Area, Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import type { DiaPrevisto, MetricasModelo, ProdutoDaLoja, UnidadeDados } from "@/domain/types";
import {
  CORES_CATEGORIA,
  HORIZONTE_DIAS,
  categorias,
  corCategoria,
  dados,
  faixaDoDia,
  historicoDiarioDe,
  nomeCategoria,
  previsaoDe,
  produtosDe,
  somar,
  unidadesDoFiltro,
  vendaDe,
} from "../../data/mockData";
import { BarraFiltros, MarcaCategoria, MiniBarras, Segmentado, StatusBadge, useFiltroLoja } from "../shared";
import { AcertoConteudo } from "./AcertoConteudo";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDiaMes, formatarNumero, formatarQtd } from "@/lib/format";

const DIAS_HISTORICO_GRAFICO = 28;

type Aba = "previsao" | "acerto";
type Visao = "categoria" | "produto";

const chave = (p: ProdutoDaLoja) => `${p.unidade}-${p.codigo}`;

export function PrevisaoSarimax() {
  const { unidade, categoria } = useFiltroLoja();
  const [aba, setAba] = useState<Aba>("previsao");
  const [visao, setVisao] = useState<Visao>("categoria");
  const [visaoTabela, setVisaoTabela] = useState<Visao>("categoria");
  const [busca, setBusca] = useState("");
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const previsao = useMemo(() => previsaoDe(unidade), [unidade]);
  const lojas = unidadesDoFiltro(unidade);
  const eventos = previsao.filter((d) => d.evento);

  // Só os produtos que têm previsão diária própria
  const produtos = useMemo(() => produtosDe(unidade, categoria, true), [unidade, categoria]);
  const filtrarBusca = (lista: ProdutoDaLoja[]) => {
    const termo = busca.trim().toLowerCase();
    return termo ? lista.filter((p) => p.nome.toLowerCase().includes(termo) || p.codigo.includes(termo)) : lista;
  };
  const produto = produtos.find((p) => chave(p) === selecionado) ?? produtos[0];

  return (
    <div className="p-6 flex flex-col gap-5">
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardContent className="p-4 flex items-center justify-between gap-4 flex-wrap">
          <BarraFiltros />
          <Segmentado
            rotulo="Ver"
            opcoes={[
              { valor: "previsao" as Aba, label: "Previsão" },
              { valor: "acerto" as Aba, label: "Como a previsão foi testada" },
            ]}
            valor={aba}
            onChange={setAba}
          />
        </CardContent>
      </Card>

      {aba === "acerto" ? (
        <AcertoConteudo />
      ) : (
        <>
          <ResumoTreino lojas={lojas} />

          {eventos.length > 0 && (
            <div className="rounded-lg px-4 py-2.5 flex items-center gap-2 text-sm" style={{ background: "#fff8e1", border: "1px solid #ffe0a0", color: "#8a5a00" }}>
              <CalendarDays size={16} />
              <span>
                {eventos.map((e) => (
                  <span key={e.data}>
                    <strong>{e.evento}</strong> em {formatarDiaMes(e.data)} ({e.dia_semana}){e.loja_fechada ? " — loja fechada, sem venda prevista." : "."}{" "}
                  </span>
                ))}
              </span>
            </div>
          )}

          {/* Previsão por categoria ou por produto */}
          <Card className="border" style={{ borderColor: "var(--border)" }}>
            <CardHeader className="pb-2 pt-4 px-5">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                  Previsão dos próximos {HORIZONTE_DIAS} dias
                </CardTitle>
                <Segmentado
                  rotulo="Por"
                  opcoes={[
                    { valor: "categoria" as Visao, label: "Categoria" },
                    { valor: "produto" as Visao, label: `Produto (${produtos.length})` },
                  ]}
                  valor={visao}
                  onChange={setVisao}
                />
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-0">
              {visao === "categoria" ? (
                <PrevisaoCategoria previsao={previsao} lojas={lojas} />
              ) : (
                <PrevisaoProduto
                  produtos={filtrarBusca(produtos)}
                  produto={produto}
                  busca={busca}
                  onBusca={setBusca}
                  onSelecionar={setSelecionado}
                  todasLojas={unidade === "todas"}
                />
              )}
            </CardContent>
          </Card>

          {/* Dia a dia */}
          <Card className="border" style={{ borderColor: "var(--border)" }}>
            <CardHeader className="pb-3 pt-4 px-5">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
                    Dia a dia · {nomeCategoria(categoria)}
                  </CardTitle>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                    Quantidade prevista em cada dia. Passe o mouse num valor para ver a faixa provável.
                  </p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  {visaoTabela === "produto" && (
                    <div className="relative">
                      <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
                      <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar produto ou código" className="h-8 text-xs pl-8 w-56" />
                    </div>
                  )}
                  <Segmentado
                    rotulo="Mostrar"
                    opcoes={[
                      { valor: "categoria" as Visao, label: "Categorias" },
                      { valor: "produto" as Visao, label: "Produtos" },
                    ]}
                    valor={visaoTabela}
                    onChange={setVisaoTabela}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-2">
              <TabelaDiaria previsao={previsao} visao={visaoTabela} produtos={filtrarBusca(produtos)} todasLojas={unidade === "todas"} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Previsão por categoria
// ---------------------------------------------------------------------------

function PrevisaoCategoria({ previsao, lojas }: { previsao: DiaPrevisto[]; lojas: UnidadeDados[] }) {
  const { unidade, categoria, setCategoria } = useFiltroLoja();
  const historico = useMemo(() => historicoDiarioDe(unidade).slice(-DIAS_HISTORICO_GRAFICO), [unidade]);
  const cor = corCategoria(categoria);

  const grafico = useMemo(() => {
    const hist = historico.map((d) => ({ data: d.data, real: vendaDe(d, categoria) }));
    const ultimo = hist[hist.length - 1]!;
    const prev = previsao.map((d) => {
      const f = faixaDoDia(d, categoria);
      return { data: d.data, previsto: f.previsto, faixa: [f.inf, f.sup] as [number, number] };
    });
    return [...hist.slice(0, -1), { ...ultimo, previsto: ultimo.real }, ...prev];
  }, [historico, previsao, categoria]);

  const faixas = previsao.map((d) => faixaDoDia(d, categoria));
  const total = somar(faixas.map((f) => f.previsto));
  const totLoja = somar(previsao.map((d) => d.previsto));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="px-3 pb-4 min-w-0">
        <div className="flex items-center gap-4 text-xs px-2 pb-2 flex-wrap" style={{ color: "var(--muted-foreground)" }}>
          <span style={{ color: "var(--foreground)", fontWeight: 600 }}>
            {nomeCategoria(categoria)} · últimos {DIAS_HISTORICO_GRAFICO} dias e próximos {HORIZONTE_DIAS}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido (sem encomendas)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: cor }} /> Previsão
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: cor, opacity: 0.18 }} /> Faixa provável
          </span>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={grafico}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={3} />
            <YAxis tick={eixo} tickFormatter={(v: number) => formatarNumero(v)} width={56} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={estiloTooltip}
              labelFormatter={(d: string) => formatarData(d)}
              formatter={(v: number | [number, number], nome: string) =>
                nome === "faixa" && Array.isArray(v)
                  ? [`${formatarNumero(v[0])} a ${formatarNumero(v[1])}`, "Faixa provável"]
                  : [formatarNumero(v as number), nome === "real" ? "Vendido" : "Previsão"]
              }
            />
            <ReferenceLine x={previsao[0]!.data} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "hoje", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
            <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.18} isAnimationActive={false} />
            <Line dataKey="real" stroke="var(--foreground)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="previsto" stroke={cor} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3, fill: cor, stroke: "#fff", strokeWidth: 1 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="border-t xl:border-t-0 xl:border-l px-5 pb-5 pt-1 flex flex-col gap-4" style={{ borderColor: "var(--border)" }}>
        <div>
          <p className="text-3xl" style={{ fontWeight: 700, lineHeight: 1, color: cor }}>
            {formatarNumero(total)}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
            unidades previstas · faixa de {formatarNumero(somar(faixas.map((f) => f.inf)))} a {formatarNumero(somar(faixas.map((f) => f.sup)))}
          </p>
        </div>
        <div className="flex flex-col gap-2">
          {categorias.map((c) => {
            const v = somar(previsao.map((d) => d.categorias[c.id].previsto));
            const ativo = categoria === c.id;
            return (
              <button key={c.id} className="flex flex-col gap-1 text-left rounded-md px-1 py-0.5 hover:bg-[var(--muted)]" onClick={() => setCategoria(ativo ? "todas" : c.id)}>
                <div className="flex items-center justify-between text-xs w-full">
                  <span className="inline-flex items-center gap-1.5" style={{ fontWeight: ativo ? 700 : 400 }}>
                    <MarcaCategoria id={c.id} /> {c.nome}
                  </span>
                  <span style={{ fontWeight: 600 }}>{formatarNumero(v)}</span>
                </div>
                <div className="h-1.5 rounded-full w-full" style={{ background: "var(--muted)" }}>
                  <div className="h-1.5 rounded-full" style={{ width: `${totLoja ? (v / totLoja) * 100 : 0}%`, background: CORES_CATEGORIA[c.id], opacity: categoria === "todas" || ativo ? 1 : 0.35 }} />
                </div>
              </button>
            );
          })}
        </div>
        <p className="text-xs flex gap-1.5 pt-3 border-t" style={{ color: "var(--muted-foreground)", borderColor: "var(--border)" }}>
          <Info size={13} className="flex-shrink-0 mt-0.5" />
          Venda do dia a dia, sem as encomendas grandes. A categoria é a parte dela na previsão {lojas.length > 1 ? "das lojas" : "da loja"}, pelo que vendeu nas
          últimas 8 semanas em cada dia da semana.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Previsão por produto
// ---------------------------------------------------------------------------

function PrevisaoProduto({
  produtos,
  produto,
  busca,
  onBusca,
  onSelecionar,
  todasLojas,
}: {
  produtos: ProdutoDaLoja[];
  produto: ProdutoDaLoja | undefined;
  busca: string;
  onBusca: (v: string) => void;
  onSelecionar: (k: string) => void;
  todasLojas: boolean;
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-[340px_minmax(0,1fr)] border-t" style={{ borderColor: "var(--border)" }}>
      <div className="border-b xl:border-b-0 xl:border-r flex flex-col" style={{ borderColor: "var(--border)" }}>
        <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
            <Input value={busca} onChange={(e) => onBusca(e.target.value)} placeholder="Buscar produto ou código" className="h-8 text-xs pl-8" />
          </div>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: 420 }}>
          {produtos.map((p) => {
            const ativo = produto && chave(produto) === chave(p);
            return (
              <button
                key={chave(p)}
                onClick={() => onSelecionar(chave(p))}
                className="w-full text-left px-4 py-2.5 flex items-center gap-3 border-b hover:bg-[var(--muted)]"
                style={{ borderColor: "var(--border)", background: ativo ? "var(--secondary)" : undefined }}
              >
                <span className="w-1 self-stretch rounded-full" style={{ background: ativo ? CORES_CATEGORIA[p.categoria] : "transparent" }} />
                <span className="flex-1 min-w-0">
                  <span className="block text-xs truncate" style={{ fontWeight: 500 }}>
                    {p.nome}
                  </span>
                  <span className="block text-[11px] truncate" style={{ color: "var(--muted-foreground)" }}>
                    {nomeCategoria(p.categoria)}
                    {todasLojas ? ` · ${p.nomeUnidade}` : ""}
                  </span>
                </span>
                <span className="text-xs text-right" style={{ fontWeight: 700 }}>
                  {formatarQtd(p.previsao_14d ?? 0)}
                </span>
              </button>
            );
          })}
          {produtos.length === 0 && (
            <p className="text-xs text-center py-8" style={{ color: "var(--muted-foreground)" }}>
              Nenhum produto encontrado.
            </p>
          )}
        </div>
      </div>
      <div className="p-5 min-w-0">{produto ? <DetalheProduto p={produto} /> : null}</div>
    </div>
  );
}

function DetalheProduto({ p }: { p: ProdutoDaLoja }) {
  const cor = CORES_CATEGORIA[p.categoria];
  const m = p.modelo?.metricas;
  const faixaTot = { inf: somar(p.previsao.map((d) => d.inf)), sup: somar(p.previsao.map((d) => d.sup)) };
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            {p.nome}
          </p>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            cód. {p.codigo} · {p.subcategoria} · {p.nomeUnidade}
          </p>
        </div>
        {p.modelo && <StatusBadge status={p.modelo.status} compacto />}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Previsto ({HORIZONTE_DIAS} dias)</p>
          <p className="text-lg" style={{ fontWeight: 700, color: cor }}>{formatarQtd(p.previsao_14d ?? 0)}</p>
          <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>faixa de {formatarQtd(faixaTot.inf)} a {formatarQtd(faixaTot.sup)}</p>
        </div>
        <div className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Vendido nas últimas 8 semanas</p>
          <p className="text-lg" style={{ fontWeight: 700 }}>{formatarQtd(p.vendido_8_semanas)}</p>
          <MiniBarras valores={p.historico_semanal} cor={cor} />
        </div>
        <div className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Acerto no total de 2 semanas</p>
          <p className="text-lg" style={{ fontWeight: 700 }}>{m ? acerto14d(m) : "—"}</p>
          <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
            {m ? `venda dentro da faixa em ${pct(m.cobertura_ic95_pct)} dos dias` : ""}
          </p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={p.previsao.map((d) => ({ ...d, faixa: [d.inf, d.sup] }))}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={1} />
          <YAxis tick={eixo} width={48} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
          <Tooltip
            contentStyle={estiloTooltip}
            labelFormatter={(d: string) => formatarData(d)}
            formatter={(v: number | [number, number], nome: string) =>
              nome === "faixa" && Array.isArray(v) ? [`${formatarQtd(v[0])} a ${formatarQtd(v[1])}`, "Faixa provável"] : [formatarQtd(v as number), "Previsão"]
            }
          />
          <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.15} isAnimationActive={false} />
          <Bar dataKey="previsto" fill={cor} radius={[4, 4, 0, 0]} barSize={16} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tabela dia a dia (itens nas linhas, dias nas colunas)
// ---------------------------------------------------------------------------

interface LinhaDiaria {
  id: string;
  nome: string;
  detalhe?: string;
  cor: string;
  dias: { previsto: number; inf: number; sup: number }[];
  destaque?: boolean;
}

function TabelaDiaria({ previsao, visao, produtos, todasLojas }: { previsao: DiaPrevisto[]; visao: Visao; produtos: ProdutoDaLoja[]; todasLojas: boolean }) {
  const { categoria } = useFiltroLoja();
  const cats = categoria === "todas" ? categorias : categorias.filter((c) => c.id === categoria);

  const linhas: LinhaDiaria[] =
    visao === "categoria"
      ? [
          ...cats.map((c) => ({ id: c.id, nome: c.nome, cor: CORES_CATEGORIA[c.id], dias: previsao.map((d) => d.categorias[c.id]) })),
          ...(categoria === "todas" ? [{ id: "total", nome: "Total", cor: "var(--foreground)", dias: previsao.map((d) => ({ previsto: d.previsto, inf: d.inf, sup: d.sup })), destaque: true }] : []),
        ]
      : produtos.map((p) => ({
          id: chave(p),
          nome: p.nome,
          detalhe: `${nomeCategoria(p.categoria)}${todasLojas ? ` · ${p.nomeUnidade}` : ""}`,
          cor: CORES_CATEGORIA[p.categoria],
          dias: p.previsao,
        }));

  const fmt = visao === "categoria" ? formatarNumero : formatarQtd;
  const fixa = "sticky left-0 z-10";

  return (
    <div className="overflow-auto border-t" style={{ borderColor: "var(--border)", maxHeight: visao === "produto" ? 520 : undefined }}>
      <table className="text-xs w-full" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0 }}>
        <thead className="sticky top-0 z-20">
          <tr>
            <th className={`${fixa} text-left pl-5 pr-3 py-2 min-w-[240px]`} style={{ background: "#eef4ea", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
              {visao === "categoria" ? "Categoria" : "Produto"}
            </th>
            {previsao.map((d) => (
              <th
                key={d.data}
                className="px-2 py-2 text-right whitespace-nowrap"
                title={d.evento ?? undefined}
                style={{ background: "#eef4ea", borderBottom: "1px solid var(--border)", fontWeight: 600, color: d.loja_fechada ? "var(--muted-foreground)" : undefined }}
              >
                <span className="block text-[10px]" style={{ fontWeight: 500, color: "var(--muted-foreground)" }}>
                  {d.dia_semana}
                  {d.evento ? " ●" : ""}
                </span>
                {formatarDiaMes(d.data)}
              </th>
            ))}
            <th className="pl-3 pr-5 py-2 text-right whitespace-nowrap" style={{ background: "#e3eedd", borderBottom: "1px solid var(--border)", fontWeight: 700 }}>
              Total {HORIZONTE_DIAS} dias
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => {
            const fundo = l.destaque ? "#f7faf5" : "#fff";
            return (
              <tr key={l.id}>
                <td className={`${fixa} pl-5 pr-3 py-2`} style={{ background: fundo, borderBottom: "1px solid var(--border)" }}>
                  <span className="inline-flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ background: l.cor }} />
                    <span>
                      <span className="block" style={{ fontWeight: l.destaque ? 700 : 500 }}>
                        {l.nome}
                      </span>
                      {l.detalhe && (
                        <span className="block text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                          {l.detalhe}
                        </span>
                      )}
                    </span>
                  </span>
                </td>
                {l.dias.map((d, i) => {
                  const fechado = previsao[i]?.loja_fechada;
                  return (
                    <td
                      key={i}
                      className="px-2 py-2 text-right"
                      title={`${formatarData(previsao[i]!.data)}: ${fmt(d.previsto)} (faixa ${fmt(d.inf)} a ${fmt(d.sup)})`}
                      style={{ background: fechado ? "#f6f7f8" : fundo, borderBottom: "1px solid var(--border)", color: fechado ? "var(--muted-foreground)" : undefined, fontWeight: l.destaque ? 700 : 400 }}
                    >
                      {fechado ? "—" : fmt(d.previsto)}
                    </td>
                  );
                })}
                <td className="pl-3 pr-5 py-2 text-right" style={{ background: "#f3f8f0", borderBottom: "1px solid var(--border)", fontWeight: 700 }}>
                  {fmt(somar(l.dias.map((d) => d.previsto)))}
                </td>
              </tr>
            );
          })}
          {linhas.length === 0 && (
            <tr>
              <td colSpan={previsao.length + 2} className="text-center py-8" style={{ color: "var(--muted-foreground)" }}>
                Nenhum produto encontrado.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <p className="text-[11px] px-5 py-2" style={{ color: "var(--muted-foreground)" }}>
        — loja fechada · ● data comemorativa (passe o mouse no dia)
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Acerto do último treino, resumido e em linguagem simples
// ---------------------------------------------------------------------------

const pct = (v: number) => `${formatarNumero(Math.round(v))}%`;
const acerto14d = (m: MetricasModelo) => (m.erro_total_14d_pct != null ? pct(Math.max(0, 100 - m.erro_total_14d_pct)) : "—");

function equilibrio(previstoSobreReal: number | null): string {
  if (previstoSobreReal == null) return "—";
  const d = previstoSobreReal - 100;
  if (Math.abs(d) < 3) return "na medida";
  return d > 0 ? `${pct(d)} acima` : `${pct(-d)} abaixo`;
}

const INDICADORES: { icone: LucideIcon; titulo: string; dica: string; valor: (m: MetricasModelo) => string }[] = [
  {
    icone: Target,
    titulo: "Acerto no total de 2 semanas",
    dica: "Quanto o total previsto para 14 dias chegou perto do que foi vendido, em média.",
    valor: acerto14d,
  },
  {
    icone: CheckCircle2,
    titulo: "Venda dentro da faixa",
    dica: "Dias em que a venda real ficou entre o mínimo e o máximo que a previsão indicou.",
    valor: (m) => pct(m.cobertura_ic95_pct),
  },
  {
    icone: TrendingUp,
    titulo: "Melhor que repetir a semana anterior",
    dica: "Testes em que a previsão errou menos do que só copiar a venda da semana passada.",
    valor: (m) => `${m.rodadas_vence_naive} de ${m.rodadas}`,
  },
  {
    icone: Scale,
    titulo: "Previsto x vendido",
    dica: "Somando todos os testes, se a previsão tende a exagerar ou a ficar curta.",
    valor: (m) => equilibrio(m.previsto_sobre_real_pct),
  },
];

function ResumoTreino({ lojas }: { lojas: UnidadeDados[] }) {
  const varias = lojas.length > 1;
  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardContent className="p-0 grid grid-cols-2 xl:grid-cols-[180px_repeat(4,minmax(0,1fr))]">
        <div className="col-span-2 xl:col-span-1 px-5 py-3 flex flex-col justify-center border-b xl:border-b-0" style={{ borderColor: "var(--border)" }}>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            Acerto da previsão
          </p>
          <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
            último treino · {formatarData(dados.gerado_em.slice(0, 10))}
          </p>
        </div>
        {INDICADORES.map((ind) => {
          const Icone = ind.icone;
          return (
            <div key={ind.titulo} className="px-4 py-3 xl:border-l" style={{ borderColor: "var(--border)" }} title={ind.dica}>
              <p className="text-[11px] inline-flex items-center gap-1.5" style={{ color: "var(--muted-foreground)", fontWeight: 600 }}>
                <Icone size={13} style={{ color: "var(--primary)" }} /> {ind.titulo}
              </p>
              {varias ? (
                <div className="mt-1 flex flex-col">
                  {lojas.map((l) => (
                    <div key={l.id} className="flex items-baseline justify-between gap-2">
                      <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                        {l.nome}
                      </span>
                      <span className="text-sm" style={{ fontWeight: 700 }}>
                        {ind.valor(l.modelo.metricas)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xl mt-0.5" style={{ fontWeight: 700 }}>
                  {ind.valor(lojas[0]!.modelo.metricas)}
                </p>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
