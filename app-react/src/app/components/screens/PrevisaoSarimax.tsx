import { useMemo, useState } from "react";
import * as DicaPrimitive from "@radix-ui/react-tooltip";
import { CalendarDays, History, Search } from "lucide-react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import type { CategoriaId, DiaPrevisto, FiltroUnidade, ProdutoDaLoja, UnidadeDados } from "@/domain/types";
import {
  CORES_CATEGORIA,
  categorias,
  historicoDiarioDe,
  horizonteEfetivo,
  nomeCategoria,
  previsaoDe,
  previsaoDoProduto,
  previstoDoProduto,
  produtosDe,
  somar,
  textoHorizonte,
  unidades,
  unidadesDoFiltro,
} from "../../data/painel";
import { FiltroHorizonte, MarcaCategoria, Segmentado, StatusBadge, useFiltroLoja } from "../shared";
import { HistoricoPrevisao } from "./HistoricoPrevisao";
import { eixo, estiloTooltip } from "@/styles/tokens";
import { formatarData, formatarDiaMes, formatarNumero, formatarQtd } from "@/lib/format";

const DIAS_HISTORICO_GRAFICO = 28;

type Aba = "previsao" | "historico";
type Visao = "categoria" | "produto";
/** O que o gráfico mostra: as 4 categorias ou uma só. */
type Foco = CategoriaId | "todas";

const chave = (p: ProdutoDaLoja) => `${p.unidade}-${p.codigo}`;
/** Rótulos do eixo das datas: ~14 no gráfico, qualquer que seja o horizonte. */
const intervaloEixo = (pontos: number) => Math.max(3, Math.ceil(pontos / 14) - 1);

// ---------------------------------------------------------------------------
// Tela: abas Previsão | Histórico de previsão (mesmo estilo das abas do Conferir Dados)
// ---------------------------------------------------------------------------

export function PrevisaoSarimax() {
  const [aba, setAba] = useState<Aba>("previsao");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const { horizonte } = useFiltroLoja();
  const abas: { id: Aba; rotulo: string; contagem?: string }[] = [
    { id: "previsao", rotulo: "Previsão", contagem: `${horizonteEfetivo(horizonte)} dias` },
    { id: "historico", rotulo: "Histórico de previsão" },
  ];

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="flex items-end gap-1 border-b" style={{ borderColor: "var(--border)" }} role="tablist">
        {abas.map((a) => {
          const ativo = aba === a.id;
          return (
            <button
              key={a.id}
              role="tab"
              aria-selected={ativo}
              onClick={() => setAba(a.id)}
              className="px-3 py-2 text-sm whitespace-nowrap -mb-px border-b-2 transition-colors"
              style={{ borderColor: ativo ? "var(--primary)" : "transparent", color: ativo ? "var(--primary)" : "var(--muted-foreground)", fontWeight: ativo ? 600 : 500 }}
            >
              {a.rotulo}
              {a.contagem && (
                <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[10px]" style={{ background: ativo ? "var(--secondary)" : "var(--muted)" }}>
                  {a.contagem}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {aba === "historico" ? (
        <HistoricoPrevisao produtoSelecionado={selecionado} onSelecionarProduto={setSelecionado} />
      ) : (
        <PainelPrevisao
          selecionado={selecionado}
          onSelecionar={setSelecionado}
          onVerHistorico={(k) => {
            setSelecionado(k);
            setAba("historico");
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Aba Previsão
// ---------------------------------------------------------------------------

function PainelPrevisao({ selecionado, onSelecionar, onVerHistorico }: { selecionado: string | null; onSelecionar: (k: string) => void; onVerHistorico: (k: string) => void }) {
  const [visao, setVisao] = useState<Visao>("categoria");
  const [visaoTabela, setVisaoTabela] = useState<Visao>("categoria");
  const [foco, setFoco] = useState<Foco>("todas");
  const [unidadeTabela, setUnidadeTabela] = useState<FiltroUnidade>("todas");
  const [busca, setBusca] = useState("");

  const lojas = unidades;
  const [unidadeFoco, setUnidadeFoco] = useState<UnidadeDados["id"]>(lojas[0]!.id);
  const lojaFoco = lojas.find((l) => l.id === unidadeFoco) ?? lojas[0]!;
  const { horizonte: escolhido } = useFiltroLoja();
  const horizonte = horizonteEfetivo(escolhido);
  const previsao = useMemo(() => previsaoDe("todas", horizonte), [horizonte]);
  const eventos = previsao.filter((d) => d.evento);

  // Só os produtos de grama com previsão neste treino: o gráfico mostra os da loja escolhida,
  // a tabela dia a dia os das lojas do filtro dela
  const buscar = (lista: ProdutoDaLoja[]) => {
    const termo = busca.trim().toLowerCase();
    return termo ? lista.filter((p) => p.nome.toLowerCase().includes(termo) || p.codigo.includes(termo)) : lista;
  };
  const produtos = useMemo(() => produtosDe(unidadeFoco, "grama", true), [unidadeFoco]);
  const filtrados = useMemo(() => buscar(produtos), [produtos, busca]);
  const produtosTabela = useMemo(() => buscar(produtosDe("todas", "grama", true)), [busca]);
  const produto = filtrados.find((p) => chave(p) === selecionado) ?? filtrados[0];

  return (
    <>
      {/* Quantos dias à frente: vale para o gráfico e para a tabela dia a dia */}
      <FiltroHorizonte />

      {eventos.length > 0 && <DatasDoPeriodo eventos={eventos} horizonte={horizonte} />}

      {/* Previsão por categoria ou por produto */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Previsão dos próximos {horizonte} dias ({textoHorizonte(horizonte)})
            </CardTitle>
            <div className="flex items-center gap-4 flex-wrap">
              <Segmentado
                rotulo="Unidade"
                opcoes={lojas.map((l) => ({ valor: l.id as UnidadeDados["id"], label: l.nome }))}
                valor={unidadeFoco}
                onChange={setUnidadeFoco}
              />
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
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          {visao === "categoria" ? (
            <PrevisaoCategoria loja={lojaFoco} foco={foco} onFoco={setFoco} primeira horizonte={horizonte} />
          ) : (
            <PrevisaoProduto
              produtos={filtrados}
              produto={produto}
              busca={busca}
              onBusca={setBusca}
              onSelecionar={onSelecionar}
              onVerHistorico={onVerHistorico}
              todasLojas={false}
              horizonte={horizonte}
            />
          )}
        </CardContent>
      </Card>

      {/* Dia a dia */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-4 px-5">
          <div>
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Dia a dia
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Quantidade prevista em cada dia. Passe o mouse num valor para ver a faixa provável.
            </p>
          </div>
          {/* Filtros fixos numa linha: a busca some ao mostrar categorias, mas guarda o lugar para os filtros não pularem */}
          <div className="mt-3 pt-3 border-t flex items-center gap-x-6 gap-y-2 flex-wrap" style={{ borderColor: "var(--border)" }}>
            <Segmentado
              rotulo="Mostrar"
              opcoes={[
                { valor: "categoria" as Visao, label: "Categorias" },
                { valor: "produto" as Visao, label: "Produtos" },
              ]}
              valor={visaoTabela}
              onChange={setVisaoTabela}
            />
            <Segmentado
              rotulo="Unidade"
              opcoes={[{ valor: "todas" as FiltroUnidade, label: "As duas lojas" }, ...unidades.map((u) => ({ valor: u.id as FiltroUnidade, label: u.nome }))]}
              valor={unidadeTabela}
              onChange={setUnidadeTabela}
            />
            <div className={`relative flex-1 min-w-[220px] ${visaoTabela === "produto" ? "" : "invisible"}`} aria-hidden={visaoTabela !== "produto"}>
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
              <Input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar produto ou código"
                disabled={visaoTabela !== "produto"}
                className="h-8 text-xs pl-8 w-full"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-2">
          <TabelaDiaria previsao={previsao} lojas={unidadesDoFiltro(unidadeTabela)} visao={visaoTabela} produtos={produtosTabela} horizonte={horizonte} />
        </CardContent>
      </Card>
    </>
  );
}

// ---------------------------------------------------------------------------
// Feriados e datas comemorativas no período mostrado
// ---------------------------------------------------------------------------

/** Situação das lojas no dia: fechadas, abertas ou só uma aberta (cada loja tem o seu calendário). */
function situacaoLojas(data: string, horizonte: number): string {
  const abertas = unidades.filter((u) => !previsaoDe(u.id, horizonte).find((d) => d.data === data)?.loja_fechada);
  if (abertas.length === 0) return unidades.length > 1 ? "Lojas fechadas" : "Loja fechada";
  if (abertas.length === unidades.length) return unidades.length > 1 ? "Lojas abertas" : "Loja aberta";
  return `Aberta só em ${abertas.map((u) => u.nome).join(", ")}`;
}

/** As datas do horizonte escolhido, no mesmo formato dos indicadores das outras telas. */
function DatasDoPeriodo({ eventos, horizonte }: { eventos: DiaPrevisto[]; horizonte: number }) {
  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardHeader className="pb-3 pt-4 px-5">
        <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
          Feriados e datas comemorativas
        </CardTitle>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
          {eventos.length === 1 ? "1 data" : `${eventos.length} datas`} nos próximos {horizonte} dias. Com a loja fechada, não há
          venda prevista.
        </p>
      </CardHeader>
      <CardContent className="px-5 pb-5">
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {eventos.map((e) => (
            <div key={e.data} className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
              <p className="text-[11px] inline-flex items-center gap-1.5" style={{ color: "var(--muted-foreground)", fontWeight: 600 }}>
                <CalendarDays size={13} style={{ color: "var(--primary)" }} /> {e.dia_semana}, {formatarDiaMes(e.data)}
              </p>
              <p className="text-sm mt-0.5" style={{ fontWeight: 700 }}>
                {e.evento}
              </p>
              <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                {situacaoLojas(e.data, horizonte)}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Previsão por categoria: as 4 categorias em linhas, uma loja por bloco
// ---------------------------------------------------------------------------

function PrevisaoCategoria({ loja, foco, onFoco, primeira, horizonte }: { loja: UnidadeDados; foco: Foco; onFoco: (f: Foco) => void; primeira: boolean; horizonte: number }) {
  const previsao = useMemo(() => previsaoDe(loja.id, horizonte), [loja.id, horizonte]);
  const historico = useMemo(() => historicoDiarioDe(loja.id).slice(-DIAS_HISTORICO_GRAFICO), [loja.id]);
  const visiveis = foco === "todas" ? categorias : categorias.filter((c) => c.id === foco);

  // Uma linha por categoria: vendido (cheia) até hoje, previsto (tracejada) depois.
  // O último dia vendido repete no previsto para as duas linhas se encontrarem.
  const grafico = useMemo(() => {
    const linhas: Record<string, string | number | [number, number]>[] = historico.map((d) => {
      const r: Record<string, string | number> = { data: d.data };
      for (const c of categorias) r[`${c.id}_real`] = d.categorias[c.id] ?? 0;
      return r;
    });
    const ultimo = linhas[linhas.length - 1]!;
    for (const c of categorias) ultimo[`${c.id}_prev`] = ultimo[`${c.id}_real`]!;
    for (const d of previsao) {
      const r: Record<string, string | number | [number, number]> = { data: d.data };
      for (const c of categorias) {
        const f = d.categorias[c.id];
        r[`${c.id}_prev`] = f.previsto;
        r[`${c.id}_faixa`] = [f.inf, f.sup];
      }
      linhas.push(r);
    }
    return linhas;
  }, [historico, previsao]);

  // Valores do painel: a previsão de hoje (1º dia previsto), mesmo com a loja fechada
  const dia = previsao[0]!;
  const totais = categorias.map((c) => ({ c, v: dia.categorias[c.id].previsto }));
  const total = somar(totais.map((t) => t.v));
  // O número grande acompanha o foco: a categoria escolhida ou a soma das 4
  const valorFoco = foco === "todas" ? total : dia.categorias[foco].previsto;
  const nomePorChave = (k: string) => {
    const [id, tipo] = [k.slice(0, k.lastIndexOf("_")), k.slice(k.lastIndexOf("_") + 1)];
    const nome = nomeCategoria(id as CategoriaId);
    return `${nome} · ${tipo === "real" ? "vendido" : tipo === "faixa" ? "faixa provável" : "previsão"}`;
  };
  const corFoco = foco === "todas" ? undefined : CORES_CATEGORIA[foco];

  return (
    <div className={`grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_380px] ${primeira ? "" : "border-t"}`} style={{ borderColor: "var(--border)" }}>
      <div className="px-3 pt-3 pb-4 min-w-0">
        <div className="flex items-center gap-4 text-xs px-2 pb-2 flex-wrap" style={{ color: "var(--muted-foreground)" }}>
          <span style={{ color: "var(--foreground)", fontWeight: 600 }}>
            {loja.nome} · {foco === "todas" ? "4 categorias" : nomeCategoria(foco)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5" style={{ background: "var(--muted-foreground)" }} /> Vendido (sem encomendas grandes)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: "var(--muted-foreground)" }} /> Previsão
          </span>
          {corFoco && (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: corFoco, opacity: 0.18 }} /> Faixa provável
            </span>
          )}
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={grafico}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={intervaloEixo(grafico.length)} />
            <YAxis tick={eixo} tickFormatter={(v: number) => formatarNumero(v)} width={56} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={estiloTooltip}
              labelFormatter={(d: string) => formatarData(d)}
              formatter={(v: number | [number, number], nome: string) =>
                Array.isArray(v) ? [`${formatarNumero(v[0])} a ${formatarNumero(v[1])}`, nomePorChave(nome)] : [formatarNumero(v), nomePorChave(nome)]
              }
            />
            <ReferenceLine x={previsao[0]!.data} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "hoje", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
            {corFoco && <Area dataKey={`${foco}_faixa`} stroke="none" fill={corFoco} fillOpacity={0.18} isAnimationActive={false} />}
            {visiveis.map((c) => (
              <Line key={`${c.id}_real`} dataKey={`${c.id}_real`} stroke={CORES_CATEGORIA[c.id]} strokeWidth={2} dot={false} isAnimationActive={false} />
            ))}
            {visiveis.map((c) => (
              <Line
                key={`${c.id}_prev`}
                dataKey={`${c.id}_prev`}
                stroke={CORES_CATEGORIA[c.id]}
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 2.5, fill: CORES_CATEGORIA[c.id], stroke: "#fff", strokeWidth: 1 }}
                isAnimationActive={false}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="border-t xl:border-t-0 xl:border-l px-5 pt-4 pb-5 flex flex-col gap-4" style={{ borderColor: "var(--border)" }}>
        <div>
          <p className="text-xs mb-1" style={{ fontWeight: 700 }}>
            {loja.nome}
          </p>
          <p className="text-3xl mt-1" style={{ fontWeight: 700, lineHeight: 1, color: foco === "todas" ? "var(--foreground)" : CORES_CATEGORIA[foco] }}>
            {formatarNumero(valorFoco)}
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <button
            className="self-start text-xs rounded-md px-2.5 py-1 border hover:bg-[var(--muted)] disabled:cursor-default disabled:hover:bg-transparent"
            style={{
              borderColor: "var(--border)",
              background: foco === "todas" ? "var(--secondary)" : undefined,
              fontWeight: foco === "todas" ? 700 : 500,
            }}
            onClick={() => onFoco("todas")}
            disabled={foco === "todas"}
            title="Mostrar as 4 categorias juntas no gráfico"
          >
            Todas as categorias
          </button>
          {totais.map(({ c, v }) => {
            const ativo = foco === c.id;
            const st = loja.categorias_modelo[c.id]?.status;
            return (
              <button
                key={c.id}
                className="flex flex-col gap-1 text-left rounded-md px-1.5 py-1 hover:bg-[var(--muted)]"
                style={{ background: ativo ? "var(--secondary)" : undefined }}
                onClick={() => onFoco(ativo ? "todas" : c.id)}
                title={ativo ? "Mostrar as 4 categorias" : `Ver só ${c.nome}, com a faixa provável`}
              >
                <div className="flex items-center justify-between gap-2 text-xs w-full">
                  <span className="inline-flex items-center gap-1.5 whitespace-nowrap" style={{ fontWeight: ativo ? 700 : 500 }}>
                    <MarcaCategoria id={c.id} /> {c.nome}
                  </span>
                  {st && <StatusBadge status={st} compacto />}
                </div>
                <div className="h-1.5 rounded-full w-full" style={{ background: "var(--muted)" }}>
                  <div
                    className="h-1.5 rounded-full"
                    style={{ width: `${total ? (v / total) * 100 : 0}%`, background: CORES_CATEGORIA[c.id], opacity: foco === "todas" || ativo ? 1 : 0.35 }}
                  />
                </div>
              </button>
            );
          })}
        </div>
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
  onVerHistorico,
  todasLojas,
  horizonte,
}: {
  produtos: ProdutoDaLoja[];
  produto: ProdutoDaLoja | undefined;
  busca: string;
  onBusca: (v: string) => void;
  onSelecionar: (k: string) => void;
  onVerHistorico: (k: string) => void;
  todasLojas: boolean;
  horizonte: number;
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
        <div className="overflow-y-auto" style={{ maxHeight: 460 }}>
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
                  {formatarQtd(previstoDoProduto(p, horizonte) ?? 0)}
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
      <div className="p-5 min-w-0">
        {produto ? <DetalheProduto p={produto} horizonte={horizonte} onVerHistorico={() => onVerHistorico(chave(produto))} /> : null}
      </div>
    </div>
  );
}

function DetalheProduto({ p, horizonte, onVerHistorico }: { p: ProdutoDaLoja; horizonte: number; onVerHistorico: () => void }) {
  const cor = CORES_CATEGORIA[p.categoria];

  // Mesmo estilo da categoria: vendido (cheia) nos últimos 28 dias, previsão (tracejada) e faixa
  const grafico = useMemo(() => {
    const hist: Record<string, string | number | [number, number]>[] = (p.historico_diario ?? []).map((d) => ({ data: d.data, real: d.vendido }));
    if (hist.length) hist[hist.length - 1]!.previsto = hist[hist.length - 1]!.real as number;
    return [...hist, ...previsaoDoProduto(p, horizonte).map((d) => ({ data: d.data, previsto: d.previsto, faixa: [d.inf, d.sup] as [number, number] }))];
  }, [p, horizonte]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm" style={{ fontWeight: 600 }}>
            {p.nome}
          </p>
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            cód. {p.codigo} · {nomeCategoria(p.categoria)} · {p.nomeUnidade}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {p.modelo && <StatusBadge status={p.modelo.status} compacto />}
          <button className="text-xs inline-flex items-center gap-1 hover:underline" style={{ color: "var(--primary)", fontWeight: 600 }} onClick={onVerHistorico}>
            <History size={13} /> Ver histórico deste produto
          </button>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs flex-wrap" style={{ color: "var(--muted-foreground)" }}>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5" style={{ background: "var(--foreground)" }} /> Vendido (sem encomendas grandes)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: cor }} /> Previsão
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-2.5 rounded-sm" style={{ background: cor, opacity: 0.18 }} /> Faixa provável
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={grafico}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="data" tickFormatter={formatarDiaMes} tick={eixo} tickLine={false} axisLine={false} interval={intervaloEixo(grafico.length)} />
          <YAxis tick={eixo} width={48} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarNumero(v)} />
          <Tooltip
            contentStyle={estiloTooltip}
            labelFormatter={(d: string) => formatarData(d)}
            formatter={(v: number | [number, number], nome: string) =>
              nome === "faixa" && Array.isArray(v)
                ? [`${formatarQtd(v[0])} a ${formatarQtd(v[1])}`, "Faixa provável"]
                : [formatarQtd(v as number), nome === "real" ? "Vendido" : "Previsão"]
            }
          />
          {p.previsao[0] && (
            <ReferenceLine x={p.previsao[0].data} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "hoje", position: "insideTopLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
          )}
          <Area dataKey="faixa" stroke="none" fill={cor} fillOpacity={0.18} isAnimationActive={false} />
          <Line dataKey="real" stroke="var(--foreground)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="previsto" stroke={cor} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3, fill: cor, stroke: "#fff", strokeWidth: 1 }} isAnimationActive={false} />
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
  unidade: string;
  nome: string;
  detalhe?: string;
  cor: string;
  dias: { previsto: number; inf: number; sup: number }[];
  /** Dias de loja fechada desta linha (cada loja tem seu calendário). */
  fechados: boolean[];
}

function TabelaDiaria({
  previsao,
  lojas,
  visao,
  produtos,
  horizonte,
}: {
  previsao: DiaPrevisto[];
  lojas: UnidadeDados[];
  visao: Visao;
  produtos: ProdutoDaLoja[];
  horizonte: number;
}) {
  const fechadosDe = (id: UnidadeDados["id"]) => previsaoDe(id, horizonte).map((d) => d.loja_fechada);

  const linhas: LinhaDiaria[] =
    visao === "categoria"
      ? lojas.flatMap((l) => {
          const prev = previsaoDe(l.id, horizonte);
          const fechados = prev.map((d) => d.loja_fechada);
          return categorias.map((c) => ({
            id: `${l.id}-${c.id}`,
            unidade: l.nome,
            nome: c.nome,
            cor: CORES_CATEGORIA[c.id],
            dias: prev.map((d) => d.categorias[c.id]),
            fechados,
          }));
        })
      : // agrupados por loja (na ordem das lojas), mantendo a ordem da lista dentro de cada uma
        lojas.flatMap((l) => produtos.filter((p) => p.unidade === l.id)).map((p) => ({
          id: chave(p),
          unidade: p.nomeUnidade,
          nome: p.nome,
          detalhe: nomeCategoria(p.categoria),
          cor: CORES_CATEGORIA[p.categoria],
          dias: previsaoDoProduto(p, horizonte),
          fechados: fechadosDe(p.unidade),
        }));

  const fmt = visao === "categoria" ? formatarNumero : formatarQtd;
  const fixa = "sticky left-0 z-10";

  return (
    <DicaPrimitive.Provider delayDuration={150} skipDelayDuration={300}>
    <div className="overflow-auto border-t" style={{ borderColor: "var(--border)", maxHeight: visao === "produto" ? 520 : undefined }}>
      <table className="text-xs w-full" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0 }}>
        <thead className="sticky top-0 z-20">
          <tr>
            <th className={`${fixa} text-left pl-5 pr-3 py-2 min-w-[240px]`} style={{ background: "#eef4ea", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
              {visao === "categoria" ? "Categoria" : "Produto"}
            </th>
            <th className="text-left px-3 py-2 whitespace-nowrap" style={{ background: "#eef4ea", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
              Unidade
            </th>
            {previsao.map((d) => {
              const th = (
                <th
                  key={d.data}
                  className="px-2 py-2 text-right whitespace-nowrap"
                  style={{ background: "#eef4ea", borderBottom: "1px solid var(--border)", fontWeight: 600 }}
                >
                  <span className="block text-[10px]" style={{ fontWeight: 500, color: "var(--muted-foreground)" }}>
                    {d.dia_semana}
                    {d.evento ? " ●" : ""}
                  </span>
                  {formatarDiaMes(d.data)}
                </th>
              );
              return d.evento ? (
                <DicaPrimitive.Root key={d.data}>
                  <DicaPrimitive.Trigger asChild>{th}</DicaPrimitive.Trigger>
                  <CaixaDica>
                    <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                      {d.dia_semana}, {formatarData(d.data)}
                    </p>
                    <p className="text-xs mt-1" style={{ fontWeight: 600 }}>
                      {d.evento}
                    </p>
                    {d.loja_fechada && (
                      <p className="text-[11px] mt-1" style={{ color: "var(--muted-foreground)" }}>
                        Loja fechada, sem venda prevista.
                      </p>
                    )}
                  </CaixaDica>
                </DicaPrimitive.Root>
              ) : (
                th
              );
            })}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l, k) => {
            // separa as lojas com uma linha mais forte quando a unidade muda
            const novaLoja = k > 0 && linhas[k - 1]!.unidade !== l.unidade;
            const borda = novaLoja ? "2px solid var(--border)" : undefined;
            const fundo = "#fff";
            return (
              <tr key={l.id}>
                <td className={`${fixa} pl-5 pr-3 py-2`} style={{ background: fundo, borderBottom: "1px solid var(--border)", borderTop: borda }}>
                  <span className="inline-flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-sm flex-shrink-0" style={{ background: l.cor }} />
                    <span>
                      <span className="block" style={{ fontWeight: 500 }}>
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
                <td className="px-3 py-2 whitespace-nowrap" style={{ background: fundo, borderBottom: "1px solid var(--border)", borderTop: borda, color: "var(--muted-foreground)" }}>
                  {l.unidade}
                </td>
                {l.dias.map((d, i) => {
                  const fechado = l.fechados[i];
                  return (
                    <DicaCelula key={i} linha={l} dia={previsao[i]!} valor={d} fechado={!!fechado} fmt={fmt}>
                      <td
                        className={`px-2 py-2 text-right ${fechado ? "" : "cursor-default hover:bg-[var(--secondary)]"}`}
                        style={{ background: fechado ? "#f6f7f8" : undefined, borderBottom: "1px solid var(--border)", borderTop: borda, color: fechado ? "var(--muted-foreground)" : undefined }}
                      >
                        {fechado ? "—" : fmt(d.previsto)}
                      </td>
                    </DicaCelula>
                  );
                })}
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
        {linhas.length > 0 && (
          <tfoot className="sticky bottom-0 z-20">
            <tr>
              <td className={`${fixa} pl-5 pr-3 py-2.5`} style={{ background: "#e3eedd", borderTop: "2px solid var(--border)", fontWeight: 700 }}>
                Total do dia
              </td>
              <td className="px-3 py-2.5 whitespace-nowrap" style={{ background: "#e3eedd", borderTop: "2px solid var(--border)", color: "var(--muted-foreground)" }}>
                {lojas.length > 1 ? "as duas lojas" : lojas[0]!.nome}
              </td>
              {previsao.map((d, i) => {
                const todasFechadas = linhas.every((l) => l.fechados[i]);
                return (
                  <td key={d.data} className="px-2 py-2.5 text-right" style={{ background: "#e3eedd", borderTop: "2px solid var(--border)", fontWeight: 700 }}>
                    {todasFechadas ? "—" : fmt(somar(linhas.map((l) => l.dias[i]!.previsto)))}
                  </td>
                );
              })}
            </tr>
          </tfoot>
        )}
      </table>
      <p className="text-[11px] px-5 py-2" style={{ color: "var(--muted-foreground)" }}>
        — loja fechada · ● data comemorativa (passe o mouse no dia)
      </p>
    </div>
    </DicaPrimitive.Provider>
  );
}

/** Caixa no estilo do tooltip dos gráficos (estiloTooltip), para as células da tabela. */
function CaixaDica({ children }: { children: React.ReactNode }) {
  return (
    <DicaPrimitive.Portal>
      <DicaPrimitive.Content
        side="top"
        sideOffset={6}
        collisionPadding={8}
        className="z-50 px-3 py-2.5 min-w-[190px] animate-in fade-in-0 zoom-in-95"
        style={{ ...estiloTooltip, color: "var(--foreground)" }}
      >
        {children}
        <DicaPrimitive.Arrow width={12} height={6} style={{ fill: "#fff", stroke: "var(--border)" }} />
      </DicaPrimitive.Content>
    </DicaPrimitive.Portal>
  );
}

/** Dica de uma célula: dia, previsão e a faixa provável, com a previsão marcada dentro da faixa. */
function DicaCelula({
  linha,
  dia,
  valor,
  fechado,
  fmt,
  children,
}: {
  linha: LinhaDiaria;
  dia: DiaPrevisto;
  valor: { previsto: number; inf: number; sup: number };
  fechado: boolean;
  fmt: (v: number) => string;
  children: React.ReactElement;
}) {
  const largura = valor.sup - valor.inf;
  const pos = largura > 0 ? Math.min(100, Math.max(0, ((valor.previsto - valor.inf) / largura) * 100)) : 50;
  return (
    <DicaPrimitive.Root>
      <DicaPrimitive.Trigger asChild>{children}</DicaPrimitive.Trigger>
      <CaixaDica>
        <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
          {dia.dia_semana}, {formatarData(dia.data)}
          {dia.evento ? ` · ${dia.evento}` : ""}
        </p>
        <p className="text-xs mt-1 inline-flex items-center gap-1.5" style={{ fontWeight: 600 }}>
          <span className="inline-block w-2 h-2 rounded-sm" style={{ background: linha.cor }} />
          {linha.nome} · {linha.unidade}
        </p>
        {fechado ? (
          <p className="text-xs mt-2" style={{ color: "var(--muted-foreground)" }}>
            Loja fechada, sem venda prevista.
          </p>
        ) : (
          <>
            <div className="flex items-baseline justify-between gap-4 mt-2">
              <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>Previsão</span>
              <span className="text-base" style={{ fontWeight: 700, lineHeight: 1 }}>{fmt(valor.previsto)}</span>
            </div>
            <div className="relative h-2.5 mt-2.5">
              <span className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1.5 rounded-full" style={{ background: linha.cor, opacity: 0.22 }} />
              <span
                className="absolute top-1/2 w-2.5 h-2.5 rounded-full -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${pos}%`, background: linha.cor, border: "2px solid #fff", boxShadow: "0 0 0 1px var(--border)" }}
              />
            </div>
            <div className="flex justify-between text-[11px] mt-1.5" style={{ color: "var(--muted-foreground)" }}>
              <span>{fmt(valor.inf)}</span>
              <span>faixa provável</span>
              <span>{fmt(valor.sup)}</span>
            </div>
          </>
        )}
      </CaixaDica>
    </DicaPrimitive.Root>
  );
}
