import { useDeferredValue, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Columns3,
  Download,
  FileSpreadsheet,
  Filter,
  Loader2,
  Search,
  X,
} from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Checkbox } from "../ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "../ui/sheet";
import type { UnidadeId } from "@/domain/types";
import { CORES_CATEGORIA, categorias, nomeUnidade } from "../../data/mockData";
import { COR_FLORES, type CategoriaAnalise } from "../../data/analises";
import { baixarCsv, baixarXlsx, type Tabela } from "@/lib/exportar";
import { formatarMesAno, formatarMoeda, formatarNumero, formatarQtd } from "@/lib/format";

/**
 * Conferir Dados: cada registro da base, mês a mês.
 *
 * Padrões de tabela de dados grandes (NN/g "Data Tables: Four Major User Tasks"; Shopify
 * Polaris IndexTable/IndexFilters; Stripe e Airtable): visões rápidas em abas, busca em
 * destaque, painel de filtros com filtros ativos em etiquetas removíveis, ordenação no
 * cabeçalho, cabeçalho fixo, escolha de colunas e densidade, linha de totais do filtro,
 * detalhe da nota num painel lateral, exportação do resultado filtrado e paginação numerada.
 *
 * Arquivos: `public/dados/registros/` (um por mês), gerados por
 *   python -m training_scripts.frontend_mock.gerar_registros_frontend   (em ia-predictor/)
 * Nomes de cliente, vendedor e operador não são exportados (dados pessoais).
 */

// ---------------------------------------------------------------------------
// Dados
// ---------------------------------------------------------------------------

interface Indice {
  lojas: UnidadeId[];
  pagamentos: string[];
  limiar_encomenda_un: number;
  total_registros: number;
  meses: { mes: string; registros: number }[];
}

type LinhaBruta = [number, number, string, string, number, number, number, number, number, 0 | 1, 0 | 1];

interface ArquivoMes {
  mes: string;
  produtos: Record<string, [string, CategoriaAnalise]>;
  linhas: LinhaBruta[];
}

interface Registro {
  i: number;
  mes: string;
  /** AAAAMMDD, para ordenar e filtrar por período */
  data: number;
  dia: number;
  loja: UnidadeId;
  nota: string;
  cod: string;
  nome: string;
  cat: CategoriaAnalise;
  qtd: number;
  unit: number;
  desc: number;
  liq: number;
  pag: string;
  cad: boolean;
  enc: boolean;
}

const BASE_DADOS = `${import.meta.env.BASE_URL}dados/registros`;
const CHAVE_PREFS = "verde-perto:conferir-dados";

const NOME_CAT: Record<CategoriaAnalise, string> = {
  ...(Object.fromEntries(categorias.map((c) => [c.id, c.nome])) as Record<string, string>),
  "flores-de-corte": "Flores de corte",
} as Record<CategoriaAnalise, string>;
const COR_CAT: Record<CategoriaAnalise, string> = { ...CORES_CATEGORIA, "flores-de-corte": COR_FLORES };
const IDS_CAT = Object.keys(NOME_CAT) as CategoriaAnalise[];
const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const COLATOR = new Intl.Collator("pt-BR");

const dataDe = (r: Registro) => `${String(r.dia).padStart(2, "0")}/${r.mes.slice(5, 7)}/${r.mes.slice(0, 4)}`;
const isoParaBr = (iso: string) => iso.split("-").reverse().join("/");

function converter(a: ArquivoMes, indice: Indice, base: number): Registro[] {
  const prefixo = Number(a.mes.replace("-", "")) * 100;
  return a.linhas.map(([dia, lj, nota, cod, qtd, unit, desc, liq, pg, cad, enc], j) => {
    const [nome, cat] = a.produtos[cod] ?? [cod, "plantas-diversas" as CategoriaAnalise];
    return {
      i: base + j, mes: a.mes, data: prefixo + dia, dia, loja: indice.lojas[lj]!, nota, cod, nome, cat,
      qtd, unit, desc, liq, pag: indice.pagamentos[pg]!, cad: !!cad, enc: !!enc,
    };
  });
}

// ---------------------------------------------------------------------------
// Colunas, visões e filtros
// ---------------------------------------------------------------------------

type ColunaId = "data" | "loja" | "nota" | "produto" | "categoria" | "qtd" | "unit" | "desc" | "liq" | "pag" | "cliente" | "tipo";

interface Coluna {
  id: ColunaId;
  titulo: string;
  numerica?: boolean;
  fixa?: boolean;
  chave: (r: Registro) => string | number;
}

const COLUNAS: Coluna[] = [
  { id: "data", titulo: "Data", fixa: true, chave: (r) => r.data },
  { id: "loja", titulo: "Loja", chave: (r) => r.loja },
  { id: "nota", titulo: "Nota", chave: (r) => Number(r.nota) || 0 },
  { id: "produto", titulo: "Produto", fixa: true, chave: (r) => r.nome },
  { id: "categoria", titulo: "Categoria", chave: (r) => NOME_CAT[r.cat] },
  { id: "qtd", titulo: "Qtd.", numerica: true, chave: (r) => r.qtd },
  { id: "unit", titulo: "Valor unit.", numerica: true, chave: (r) => r.unit },
  { id: "desc", titulo: "Desconto", numerica: true, chave: (r) => r.desc },
  { id: "liq", titulo: "Valor líquido", numerica: true, chave: (r) => r.liq },
  { id: "pag", titulo: "Pagamento", chave: (r) => r.pag },
  { id: "cliente", titulo: "Cliente", chave: (r) => (r.cad ? 1 : 0) },
  { id: "tipo", titulo: "Tipo", chave: (r) => (r.enc ? 1 : 0) },
];

type Visao = "todos" | "encomendas" | "cadastrados" | "descontos" | "devolucoes";
const VISOES: { id: Visao; rotulo: string; teste: (r: Registro) => boolean }[] = [
  { id: "todos", rotulo: "Todos", teste: () => true },
  { id: "encomendas", rotulo: "Encomendas", teste: (r) => r.enc },
  { id: "cadastrados", rotulo: "Clientes cadastrados", teste: (r) => r.cad },
  { id: "descontos", rotulo: "Com desconto", teste: (r) => r.desc > 0 },
  { id: "devolucoes", rotulo: "Devoluções", teste: (r) => r.liq < 0 || r.qtd < 0 },
];

interface Filtros {
  lojas: UnidadeId[];
  categorias: CategoriaAnalise[];
  pagamentos: string[];
  cliente: "todos" | "consumidor" | "cadastrado";
  tipo: "todos" | "dia" | "encomenda";
  dataDe: string;
  dataAte: string;
  valorMin: string;
  valorMax: string;
}

const FILTROS_VAZIOS: Filtros = {
  lojas: [],
  categorias: [],
  pagamentos: [],
  cliente: "todos",
  tipo: "todos",
  dataDe: "",
  dataAte: "",
  valorMin: "",
  valorMax: "",
};

type Ordem = { col: ColunaId; dir: "asc" | "desc" } | null;

interface Prefs {
  ocultas: ColunaId[];
  tamanho: number;
}

function lerPrefs(): Prefs {
  try {
    const p = JSON.parse(localStorage.getItem(CHAVE_PREFS) ?? "null");
    if (p && Array.isArray(p.ocultas)) return { ocultas: p.ocultas, tamanho: Number(p.tamanho) || 50 };
  } catch {
    /* sem armazenamento: usa o padrão */
  }
  return { ocultas: ["unit", "desc"], tamanho: 50 };
}

const numOuNulo = (s: string) => (s.trim() === "" || Number.isNaN(Number(s.replace(",", "."))) ? null : Number(s.replace(",", ".")));

/** Monta o teste uma vez por mudança de filtro (a base inteira tem ~345 mil linhas). */
function criarFiltro(f: Filtros, termo: string, codsBusca: Set<string> | null): (r: Registro) => boolean {
  const lojas = new Set(f.lojas);
  const cats = new Set(f.categorias);
  const pags = new Set(f.pagamentos);
  const de = f.dataDe ? Number(f.dataDe.replaceAll("-", "")) : null;
  const ate = f.dataAte ? Number(f.dataAte.replaceAll("-", "")) : null;
  const vmin = numOuNulo(f.valorMin);
  const vmax = numOuNulo(f.valorMax);
  return (r) => {
    if (lojas.size && !lojas.has(r.loja)) return false;
    if (cats.size && !cats.has(r.cat)) return false;
    if (pags.size && !pags.has(r.pag)) return false;
    if (f.cliente === "consumidor" && r.cad) return false;
    if (f.cliente === "cadastrado" && !r.cad) return false;
    if (f.tipo === "dia" && r.enc) return false;
    if (f.tipo === "encomenda" && !r.enc) return false;
    if (de !== null && r.data < de) return false;
    if (ate !== null && r.data > ate) return false;
    if (vmin !== null && r.liq < vmin) return false;
    if (vmax !== null && r.liq > vmax) return false;
    if (codsBusca && !codsBusca.has(r.cod) && !r.nota.includes(termo)) return false;
    return true;
  };
}

/** Ordena por chave numérica; textos viram a posição na lista de valores únicos já ordenada. */
function ordenar(lista: Registro[], col: Coluna, dir: "asc" | "desc"): Registro[] {
  const chaves = lista.map(col.chave);
  let num: number[];
  if (chaves.some((k) => typeof k === "string")) {
    const unicos = [...new Set(chaves.map(String))].sort(COLATOR.compare);
    const pos = new Map(unicos.map((u, k) => [u, k]));
    num = chaves.map((k) => pos.get(String(k))!);
  } else num = chaves as number[];
  const s = dir === "asc" ? 1 : -1;
  const idx = lista.map((_, k) => k);
  idx.sort((a, b) => (num[a]! - num[b]!) * s || a - b);
  return idx.map((k) => lista[k]!);
}

/** Números de página com reticências: 1 … 4 5 [6] 7 8 … 383 */
function paginasVisiveis(atual: number, total: number): (number | "…")[] {
  const set = new Set([1, total, atual - 2, atual - 1, atual, atual + 1, atual + 2].filter((p) => p >= 1 && p <= total));
  const lista = [...set].sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  lista.forEach((p, i) => {
    if (i && p - lista[i - 1]! > 1) out.push("…");
    out.push(p);
  });
  return out;
}

// ---------------------------------------------------------------------------
// Peças
// ---------------------------------------------------------------------------

function Etiqueta({ children, onRemover }: { children: ReactNode; onRemover: () => void }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full pl-2.5 pr-1 py-0.5 text-xs"
      style={{ background: "var(--secondary)", color: "var(--secondary-foreground)", border: "1px solid var(--border)" }}
    >
      {children}
      <button onClick={onRemover} className="rounded-full p-0.5 hover:bg-white" aria-label="Remover filtro">
        <X size={11} />
      </button>
    </span>
  );
}

function ListaMarcavel<T extends string>({ opcoes, marcados, onChange, colunas = 1 }: { opcoes: { valor: T; label: ReactNode }[]; marcados: T[]; onChange: (v: T[]) => void; colunas?: 1 | 2 }) {
  return (
    <div className={colunas === 2 ? "grid grid-cols-2 gap-x-4 gap-y-1.5" : "flex flex-col gap-1.5"}>
      {opcoes.map((o) => {
        const ativo = marcados.includes(o.valor);
        return (
          <label key={o.valor} className="flex items-center gap-2 text-xs cursor-pointer">
            <Checkbox checked={ativo} onCheckedChange={(v) => onChange(v ? [...marcados, o.valor] : marcados.filter((x) => x !== o.valor))} />
            {o.label}
          </label>
        );
      })}
    </div>
  );
}

function Escolha<T extends string>({ opcoes, valor, onChange }: { opcoes: { valor: T; label: string }[]; valor: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-md p-0.5 gap-0.5" style={{ background: "var(--muted)" }}>
      {opcoes.map((o) => (
        <button
          key={o.valor}
          onClick={() => onChange(o.valor)}
          className="px-2.5 py-1 rounded text-xs"
          style={{ background: valor === o.valor ? "#fff" : "transparent", color: valor === o.valor ? "var(--primary)" : "var(--muted-foreground)", fontWeight: valor === o.valor ? 600 : 500 }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

const SecaoFiltro = ({ titulo, children }: { titulo: string; children: ReactNode }) => (
  <div className="flex flex-col gap-2">
    <p className="text-[11px] uppercase tracking-wide" style={{ color: "var(--muted-foreground)", fontWeight: 700 }}>
      {titulo}
    </p>
    {children}
  </div>
);

function SeletorMeses({ meses, selecionados, onChange }: { meses: Indice["meses"]; selecionados: string[]; onChange: (v: string[]) => void }) {
  const todos = selecionados.length === meses.length;
  const existentes = new Map(meses.map((m) => [m.mes, m.registros]));
  const anos = [...new Set(meses.map((m) => m.mes.slice(0, 4)))];
  const totalSel = selecionados.reduce((s, m) => s + (existentes.get(m) ?? 0), 0);
  const ordenados = (l: string[]) => meses.map((m) => m.mes).filter((m) => l.includes(m));
  const marcar = (lista: string[], ligar: boolean) =>
    onChange(ligar ? ordenados([...new Set([...selecionados, ...lista])]) : selecionados.filter((m) => !lista.includes(m)));
  const rotulo = todos
    ? "Todos os meses"
    : selecionados.length === 0
      ? "Nenhum mês"
      : selecionados.length <= 2
        ? selecionados.map(formatarMesAno).join(", ")
        : `${selecionados.length} meses`;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
          <CalendarDays size={14} /> {rotulo}
          <ChevronDown size={13} style={{ opacity: 0.6 }} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[330px] p-0">
        <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ fontWeight: 600 }}>
            <Checkbox checked={todos} onCheckedChange={(v) => onChange(v ? meses.map((m) => m.mes) : [])} /> Todos os meses
          </label>
          <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
            {formatarNumero(totalSel)} registros
          </span>
        </div>
        <div className="p-4 flex flex-col gap-4">
          {anos.map((ano) => {
            const doAno = meses.filter((m) => m.mes.startsWith(ano)).map((m) => m.mes);
            const anoTodo = doAno.every((m) => selecionados.includes(m));
            return (
              <div key={ano} className="flex flex-col gap-2">
                <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ fontWeight: 700 }}>
                  <Checkbox checked={anoTodo} onCheckedChange={(v) => marcar(doAno, !!v)} /> {ano}
                </label>
                <div className="grid grid-cols-6 gap-1">
                  {MESES_CURTOS.map((nome, k) => {
                    const mes = `${ano}-${String(k + 1).padStart(2, "0")}`;
                    const n = existentes.get(mes);
                    const ativo = selecionados.includes(mes);
                    return (
                      <button
                        key={mes}
                        disabled={n === undefined}
                        onClick={() => marcar([mes], !ativo)}
                        title={n === undefined ? "Sem dados neste mês" : `${formatarNumero(n)} registros`}
                        className="rounded-md py-1.5 text-xs border disabled:cursor-not-allowed"
                        style={{
                          background: ativo ? "var(--secondary)" : "#fff",
                          borderColor: ativo ? "var(--primary)" : "var(--border)",
                          color: n === undefined ? "#c3c8ce" : ativo ? "var(--primary)" : "var(--foreground)",
                          fontWeight: ativo ? 600 : 500,
                        }}
                      >
                        {nome}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Tela
// ---------------------------------------------------------------------------

export function PreVisualizacao() {
  const [indice, setIndice] = useState<Indice | null>(null);
  const [porMes, setPorMes] = useState<Record<string, Registro[]>>({});
  const [produtos, setProdutos] = useState<Record<string, [string, CategoriaAnalise]>>({});
  const [meses, setMeses] = useState<string[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  const [visao, setVisao] = useState<Visao>("todos");
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VAZIOS);
  const [busca, setBusca] = useState("");
  const termo = useDeferredValue(busca.trim().toLowerCase());
  const filtrosAdiados = useDeferredValue(filtros);
  const mesesAdiados = useDeferredValue(meses);
  const [ordem, setOrdem] = useState<Ordem>({ col: "data", dir: "desc" });
  const [pagina, setPagina] = useState(1);
  const [prefs, setPrefs] = useState<Prefs>(lerPrefs);
  const [notaAberta, setNotaAberta] = useState<Registro | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE_PREFS, JSON.stringify(prefs));
    } catch {
      /* preferências só nesta visita */
    }
  }, [prefs]);

  useEffect(() => {
    fetch(`${BASE_DADOS}/indice.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((i: Indice) => {
        setIndice(i);
        setMeses(i.meses.map((m) => m.mes));
      })
      .catch(() => setErro("Não foi possível carregar a lista de meses da base."));
  }, []);

  // Todos os meses entram por padrão: carrega os arquivos mensais em paralelo, do mais recente ao mais antigo.
  useEffect(() => {
    if (!indice) return;
    let vivo = true;
    indice.meses
      .map((m, k) => ({ mes: m.mes, k }))
      .reverse()
      .forEach(({ mes, k }) =>
        fetch(`${BASE_DADOS}/${mes}.json`)
          .then((r) => (r.ok ? r.json() : Promise.reject()))
          .then((a: ArquivoMes) => {
            if (!vivo) return;
            setPorMes((p) => ({ ...p, [mes]: converter(a, indice, k * 1_000_000) }));
            setProdutos((p) => ({ ...p, ...a.produtos }));
          })
          .catch(() => vivo && setErro(`Não foi possível carregar os registros de ${formatarMesAno(mes)}.`)),
      );
    return () => {
      vivo = false;
    };
  }, [indice]);

  const faltam = meses.filter((m) => !porMes[m]).length;
  // o valor adiado fica vazio por um quadro logo após o índice chegar
  const carregando = faltam > 0 || (mesesAdiados.length === 0 && meses.length > 0);
  const registros = useMemo<Registro[]>(
    () => (carregando ? [] : mesesAdiados.flatMap((m) => porMes[m] ?? [])),
    [porMes, mesesAdiados, carregando],
  );
  const codsBusca = useMemo(
    () =>
      termo
        ? new Set(Object.entries(produtos).filter(([c, [n]]) => c.toLowerCase().includes(termo) || n.toLowerCase().includes(termo)).map(([c]) => c))
        : null,
    [produtos, termo],
  );

  // Filtros + busca (sem a visão), para as contagens das abas
  const base = useMemo(() => registros.filter(criarFiltro(filtrosAdiados, termo, codsBusca)), [registros, filtrosAdiados, termo, codsBusca]);
  const contagemVisao = useMemo(() => Object.fromEntries(VISOES.map((v) => [v.id, base.filter(v.teste).length])) as Record<Visao, number>, [base]);
  const filtrados = useMemo(() => {
    const teste = VISOES.find((v) => v.id === visao)!.teste;
    const lista = base.filter(teste);
    return ordem ? ordenar(lista, COLUNAS.find((c) => c.id === ordem.col)!, ordem.dir) : lista;
  }, [base, visao, ordem]);

  useEffect(() => setPagina(1), [meses, visao, filtros, termo, ordem, prefs.tamanho]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / prefs.tamanho));
  const paginaAtual = Math.min(pagina, totalPaginas);
  const visiveis = filtrados.slice((paginaAtual - 1) * prefs.tamanho, paginaAtual * prefs.tamanho);
  const totQtd = filtrados.reduce((s, r) => s + r.qtd, 0);
  const totLiq = filtrados.reduce((s, r) => s + r.liq, 0);
  const totDesc = filtrados.reduce((s, r) => s + r.desc, 0);
  const notasNoFiltro = useMemo(() => new Set(filtrados.map((r) => `${r.loja}-${r.data}-${r.nota}`)).size, [filtrados]);

  const colunas = COLUNAS.filter((c) => !prefs.ocultas.includes(c.id));
  const celula = "px-3 py-2.5";
  const todosMeses = !!indice && meses.length === indice.meses.length;
  const primeiroDia = indice ? `${indice.meses[0]!.mes}-01` : undefined;
  const ultimoDia = indice
    ? (() => {
        const m = indice.meses[indice.meses.length - 1]!.mes;
        return `${m}-${String(new Date(Number(m.slice(0, 4)), Number(m.slice(5, 7)), 0).getDate()).padStart(2, "0")}`;
      })()
    : undefined;
  const limparTudo = () => {
    setFiltros(FILTROS_VAZIOS);
    setBusca("");
    setVisao("todos");
    if (indice) setMeses(indice.meses.map((m) => m.mes));
  };

  const set = <K extends keyof Filtros>(k: K, v: Filtros[K]) => setFiltros((f) => ({ ...f, [k]: v }));
  const nFiltros =
    filtros.lojas.length + filtros.categorias.length + filtros.pagamentos.length + (filtros.cliente !== "todos" ? 1 : 0) + (filtros.tipo !== "todos" ? 1 : 0) +
    (filtros.dataDe || filtros.dataAte ? 1 : 0) + (filtros.valorMin || filtros.valorMax ? 1 : 0);
  const algumFiltro = nFiltros > 0 || busca !== "" || visao !== "todos" || !todosMeses;

  const alternarOrdem = (col: ColunaId) =>
    setOrdem((o) => (!o || o.col !== col ? { col, dir: "asc" } : o.dir === "asc" ? { col, dir: "desc" } : null));

  const itensNota = useMemo(
    () => (notaAberta ? registros.filter((r) => r.nota === notaAberta.nota && r.loja === notaAberta.loja && r.data === notaAberta.data) : []),
    [notaAberta, registros],
  );

  const exportar = (formato: "xlsx" | "csv") => {
    const tabela: Tabela = {
      colunas: [
        { titulo: "Data", tipo: "texto" },
        { titulo: "Loja", tipo: "texto" },
        { titulo: "Nota", tipo: "texto" },
        { titulo: "Código", tipo: "texto" },
        { titulo: "Produto", tipo: "texto" },
        { titulo: "Categoria", tipo: "texto" },
        { titulo: "Quantidade", tipo: "numero" },
        { titulo: "Valor unitário", tipo: "decimal" },
        { titulo: "Desconto", tipo: "decimal" },
        { titulo: "Valor líquido", tipo: "decimal" },
        { titulo: "Pagamento", tipo: "texto" },
        { titulo: "Cliente", tipo: "texto" },
        { titulo: "Tipo", tipo: "texto" },
      ],
      linhas: filtrados.map((r) => [
        dataDe(r), nomeUnidade(r.loja), r.nota, r.cod, r.nome, NOME_CAT[r.cat], r.qtd, r.unit, r.desc, r.liq, r.pag,
        r.cad ? "Cadastrado" : "Consumidor", r.enc ? "Encomenda" : "Dia a dia",
      ]),
    };
    const nome = todosMeses ? "registros-todos-os-meses" : meses.length === 1 ? `registros-${meses[0]}` : `registros-${meses[0]}-a-${meses[meses.length - 1]}`;
    if (formato === "csv") baixarCsv(tabela, nome);
    else baixarXlsx(tabela, nome, "Registros");
  };

  const renderCelula = (c: Coluna, r: Registro) => {
    switch (c.id) {
      case "data":
        return <span className="whitespace-nowrap">{dataDe(r)}</span>;
      case "loja":
        return <span className="whitespace-nowrap">{nomeUnidade(r.loja)}</span>;
      case "nota":
        return <span style={{ color: "var(--muted-foreground)" }}>{r.nota}</span>;
      case "produto":
        return (
          <div className="min-w-[220px]">
            <p style={{ fontWeight: 500 }}>{r.nome}</p>
            <p style={{ color: "var(--muted-foreground)" }}>cód. {r.cod}</p>
          </div>
        );
      case "categoria":
        return (
          <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: COR_CAT[r.cat] }} /> {NOME_CAT[r.cat]}
          </span>
        );
      case "qtd":
        return formatarQtd(r.qtd);
      case "unit":
        return <span className="whitespace-nowrap">{formatarMoeda(r.unit)}</span>;
      case "desc":
        return r.desc ? <span className="whitespace-nowrap">{formatarMoeda(r.desc)}</span> : <span style={{ color: "var(--muted-foreground)" }}>—</span>;
      case "liq":
        return (
          <span className="whitespace-nowrap" style={{ fontWeight: 600, color: r.liq < 0 ? "var(--destructive)" : undefined }}>
            {formatarMoeda(r.liq)}
          </span>
        );
      case "pag":
        return <span className="whitespace-nowrap">{r.pag}</span>;
      case "cliente":
        return <span style={{ color: "var(--muted-foreground)" }}>{r.cad ? "Cadastrado" : "Consumidor"}</span>;
      case "tipo":
        return r.enc ? (
          <span className="inline-flex rounded-full px-2 py-0.5 text-[11px] whitespace-nowrap" style={{ background: "#f1f3f5", color: "#3d4651", border: "1px solid #d8dce1", fontWeight: 600 }}>
            encomenda
          </span>
        ) : (
          <span className="whitespace-nowrap" style={{ color: "var(--muted-foreground)" }}>
            dia a dia
          </span>
        );
    }
  };

  const etiquetas: { chave: string; texto: string; remover: () => void }[] = [
    ...(!todosMeses && indice
      ? [{
          chave: "meses",
          texto: `Meses: ${meses.length === 0 ? "nenhum" : meses.length <= 3 ? meses.map(formatarMesAno).join(", ") : `${meses.length} de ${indice.meses.length}`}`,
          remover: () => setMeses(indice.meses.map((m) => m.mes)),
        }]
      : []),
    ...filtros.lojas.map((l) => ({ chave: `l${l}`, texto: `Loja: ${nomeUnidade(l)}`, remover: () => set("lojas", filtros.lojas.filter((x) => x !== l)) })),
    ...filtros.categorias.map((c) => ({ chave: `c${c}`, texto: `Categoria: ${NOME_CAT[c]}`, remover: () => set("categorias", filtros.categorias.filter((x) => x !== c)) })),
    ...filtros.pagamentos.map((p) => ({ chave: `p${p}`, texto: `Pagamento: ${p}`, remover: () => set("pagamentos", filtros.pagamentos.filter((x) => x !== p)) })),
    ...(filtros.cliente !== "todos" ? [{ chave: "cli", texto: `Cliente: ${filtros.cliente === "cadastrado" ? "cadastrado" : "consumidor"}`, remover: () => set("cliente", "todos") }] : []),
    ...(filtros.tipo !== "todos" ? [{ chave: "tipo", texto: `Tipo: ${filtros.tipo === "encomenda" ? "encomenda" : "dia a dia"}`, remover: () => set("tipo", "todos") }] : []),
    ...(filtros.dataDe || filtros.dataAte
      ? [{
          chave: "periodo",
          texto: `Período: ${filtros.dataDe ? isoParaBr(filtros.dataDe) : "início"} a ${filtros.dataAte ? isoParaBr(filtros.dataAte) : "fim"}`,
          remover: () => setFiltros((f) => ({ ...f, dataDe: "", dataAte: "" })),
        }]
      : []),
    ...(filtros.valorMin || filtros.valorMax
      ? [{ chave: "val", texto: `Valor: ${filtros.valorMin ? `de R$ ${filtros.valorMin}` : ""} ${filtros.valorMax ? `até R$ ${filtros.valorMax}` : ""}`.trim(), remover: () => setFiltros((f) => ({ ...f, valorMin: "", valorMax: "" })) }]
      : []),
  ];

  return (
    <div className="p-6">
      <div className="rounded-xl border bg-white flex flex-col" style={{ borderColor: "var(--border)" }}>
        {/* Cabeçalho */}
        <div className="px-5 pt-5 pb-3 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-sm" style={{ fontWeight: 600 }}>
              Registros de venda
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Cada linha das planilhas carregadas ({indice ? formatarNumero(indice.total_registros) : "…"} registros, sem fretes e serviços). Clique numa linha para ver a nota
              inteira. Nomes de cliente, vendedor e operador não são exibidos.
            </p>
          </div>
          {indice && <SeletorMeses meses={indice.meses} selecionados={meses} onChange={setMeses} />}
        </div>

        {/* Visões rápidas */}
        <div className="px-5 flex items-end gap-1 border-b overflow-x-auto overflow-y-hidden" style={{ borderColor: "var(--border)" }} role="tablist">
          {VISOES.map((v) => {
            const ativo = visao === v.id;
            return (
              <button
                key={v.id}
                role="tab"
                aria-selected={ativo}
                onClick={() => setVisao(v.id)}
                className="px-3 py-2 text-xs whitespace-nowrap -mb-px border-b-2 transition-colors"
                style={{ borderColor: ativo ? "var(--primary)" : "transparent", color: ativo ? "var(--primary)" : "var(--muted-foreground)", fontWeight: ativo ? 600 : 500 }}
              >
                {v.rotulo}
                <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[10px]" style={{ background: ativo ? "var(--secondary)" : "var(--muted)" }}>
                  {formatarNumero(contagemVisao[v.id] ?? 0)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Barra de ferramentas */}
        <div className="px-5 py-3 flex items-center gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[240px] max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
            <Input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por produto, código ou nº da nota" className="h-9 text-xs pl-9" />
            {busca && (
              <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1" onClick={() => setBusca("")} aria-label="Limpar busca">
                <X size={13} />
              </button>
            )}
          </div>

          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
                <Filter size={14} /> Filtros
                {nFiltros > 0 && (
                  <span className="rounded-full px-1.5 text-[10px] text-white" style={{ background: "var(--primary)" }}>
                    {nFiltros}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-[520px] p-0">
              <div className="p-4 grid grid-cols-2 gap-5 max-h-[60vh] overflow-y-auto">
                <SecaoFiltro titulo="Loja">
                  <ListaMarcavel opcoes={(indice?.lojas ?? []).map((l) => ({ valor: l, label: nomeUnidade(l) }))} marcados={filtros.lojas} onChange={(v) => set("lojas", v)} />
                </SecaoFiltro>
                <SecaoFiltro titulo="Categoria">
                  <ListaMarcavel
                    opcoes={IDS_CAT.map((c) => ({
                      valor: c,
                      label: (
                        <span className="inline-flex items-center gap-1.5">
                          <span className="inline-block w-2 h-2 rounded-sm" style={{ background: COR_CAT[c] }} /> {NOME_CAT[c]}
                        </span>
                      ),
                    }))}
                    marcados={filtros.categorias}
                    onChange={(v) => set("categorias", v)}
                  />
                </SecaoFiltro>
                <SecaoFiltro titulo="Cliente">
                  <Escolha opcoes={[{ valor: "todos", label: "Todos" }, { valor: "consumidor", label: "Consumidor" }, { valor: "cadastrado", label: "Cadastrado" }]} valor={filtros.cliente} onChange={(v) => set("cliente", v)} />
                </SecaoFiltro>
                <SecaoFiltro titulo="Tipo de venda">
                  <Escolha opcoes={[{ valor: "todos", label: "Todos" }, { valor: "dia", label: "Dia a dia" }, { valor: "encomenda", label: "Encomenda" }]} valor={filtros.tipo} onChange={(v) => set("tipo", v)} />
                </SecaoFiltro>
                <SecaoFiltro titulo="Período">
                  <div className="flex items-center gap-2">
                    <Input type="date" min={primeiroDia} max={ultimoDia} value={filtros.dataDe} onChange={(e) => set("dataDe", e.target.value)} className="h-8 text-xs w-[124px] px-2" />
                    <span className="text-xs">a</span>
                    <Input type="date" min={primeiroDia} max={ultimoDia} value={filtros.dataAte} onChange={(e) => set("dataAte", e.target.value)} className="h-8 text-xs w-[124px] px-2" />
                  </div>
                </SecaoFiltro>
                <SecaoFiltro titulo="Valor líquido da linha (R$)">
                  <div className="flex items-center gap-2">
                    <Input value={filtros.valorMin} onChange={(e) => set("valorMin", e.target.value)} placeholder="mínimo" className="h-8 text-xs w-24" />
                    <span className="text-xs">a</span>
                    <Input value={filtros.valorMax} onChange={(e) => set("valorMax", e.target.value)} placeholder="máximo" className="h-8 text-xs w-24" />
                  </div>
                </SecaoFiltro>
                <div className="col-span-2">
                  <SecaoFiltro titulo="Forma de pagamento">
                    <ListaMarcavel colunas={2} opcoes={(indice?.pagamentos ?? []).map((p) => ({ valor: p, label: p }))} marcados={filtros.pagamentos} onChange={(v) => set("pagamentos", v)} />
                  </SecaoFiltro>
                </div>
              </div>
              <div className="px-4 py-2.5 border-t flex justify-between items-center" style={{ borderColor: "var(--border)" }}>
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  {formatarNumero(filtrados.length)} registros com estes filtros
                </span>
                <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => setFiltros(FILTROS_VAZIOS)} disabled={nFiltros === 0}>
                  Limpar filtros
                </Button>
              </div>
            </PopoverContent>
          </Popover>

          <div className="ml-auto flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
                  <Columns3 size={14} /> Colunas
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel className="text-xs">Colunas visíveis</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {COLUNAS.map((c) => (
                  <DropdownMenuCheckboxItem
                    key={c.id}
                    className="text-xs"
                    disabled={c.fixa}
                    checked={!prefs.ocultas.includes(c.id)}
                    onSelect={(e) => e.preventDefault()}
                    onCheckedChange={(v) => setPrefs((p) => ({ ...p, ocultas: v ? p.ocultas.filter((x) => x !== c.id) : [...p.ocultas, c.id] }))}
                  >
                    {c.titulo}
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" className="h-9 gap-1.5 text-xs" style={{ background: "var(--primary)", color: "#fff" }} disabled={!filtrados.length}>
                  <Download size={14} /> Exportar
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel className="text-xs">{formatarNumero(filtrados.length)} registros filtrados</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-xs gap-2" onClick={() => exportar("xlsx")}>
                  <FileSpreadsheet size={13} /> Excel (.xlsx)
                </DropdownMenuItem>
                <DropdownMenuItem className="text-xs gap-2" onClick={() => exportar("csv")}>
                  <Download size={13} /> CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Filtros ativos */}
        {(etiquetas.length > 0 || algumFiltro) && (
          <div className="px-5 pb-3 flex items-center gap-1.5 flex-wrap">
            {etiquetas.map((e) => (
              <Etiqueta key={e.chave} onRemover={e.remover}>
                {e.texto}
              </Etiqueta>
            ))}
            {algumFiltro && (
              <button
                className="text-xs ml-1 hover:underline"
                style={{ color: "var(--primary)", fontWeight: 600 }}
                onClick={limparTudo}
              >
                Limpar tudo
              </button>
            )}
          </div>
        )}

        {/* Tabela */}
        {erro ? (
          <p className="text-xs px-5 py-16 text-center border-t" style={{ color: "var(--destructive)", borderColor: "var(--border)" }}>
            {erro}
          </p>
        ) : !indice || carregando ? (
          <p className="text-xs px-5 py-16 flex items-center justify-center gap-2 border-t" style={{ color: "var(--muted-foreground)", borderColor: "var(--border)" }}>
            <Loader2 size={14} className="animate-spin" /> Carregando registros
            {indice ? ` · ${formatarNumero(meses.length - faltam)} de ${formatarNumero(meses.length)} meses` : "…"}
          </p>
        ) : (
          <div className="overflow-auto border-t" style={{ borderColor: "var(--border)", maxHeight: "calc(100vh - 360px)", minHeight: 320 }}>
            <table className="w-full text-xs" style={{ fontVariantNumeric: "tabular-nums" }}>
              <thead className="sticky top-0 z-10" style={{ background: "#eef4ea" }}>
                <tr>
                  {colunas.map((c, j) => {
                    const ativa = ordem?.col === c.id;
                    const Icone = ativa ? (ordem!.dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
                    return (
                      <th
                        key={c.id}
                        className={`${celula} ${j === 0 ? "pl-5" : ""} ${c.numerica ? "text-right" : "text-left"} text-xs whitespace-nowrap`}
                        style={{ fontWeight: 600, borderBottom: "1px solid var(--border)" }}
                        aria-sort={ativa ? (ordem!.dir === "asc" ? "ascending" : "descending") : "none"}
                      >
                        <button
                          onClick={() => alternarOrdem(c.id)}
                          className={`inline-flex items-center gap-1 text-xs hover:text-[var(--primary)] ${c.numerica ? "flex-row-reverse" : ""}`}
                          style={{ color: ativa ? "var(--primary)" : "var(--foreground)" }}
                          title="Ordenar"
                        >
                          {c.titulo}
                          <Icone size={12} style={{ opacity: ativa ? 1 : 0.35 }} />
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {visiveis.map((r) => (
                  <tr
                    key={r.i}
                    tabIndex={0}
                    onClick={() => setNotaAberta(r)}
                    onKeyDown={(e) => e.key === "Enter" && setNotaAberta(r)}
                    className="cursor-pointer hover:bg-[var(--secondary)] focus:outline-none focus:bg-[var(--secondary)]"
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    {colunas.map((c, j) => (
                      <td key={c.id} className={`${celula} ${j === 0 ? "pl-5" : ""} ${c.numerica ? "text-right" : ""}`}>
                        {renderCelula(c, r)}
                      </td>
                    ))}
                  </tr>
                ))}
                {visiveis.length === 0 && (
                  <tr>
                    <td colSpan={colunas.length} className="py-16 text-center" style={{ color: "var(--muted-foreground)" }}>
                      <p>{meses.length === 0 ? "Nenhum mês selecionado." : "Nenhum registro com esses filtros nos meses selecionados."}</p>
                      {algumFiltro && (
                        <button
                          className="mt-2 text-xs hover:underline"
                          style={{ color: "var(--primary)", fontWeight: 600 }}
                          onClick={limparTudo}
                        >
                          Limpar filtros
                        </button>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
              {filtrados.length > 0 && (
                <tfoot className="sticky bottom-0" style={{ background: "#f7faf5" }}>
                  <tr style={{ borderTop: "2px solid var(--border)" }}>
                    {colunas.map((c, j) => (
                      <td key={c.id} className={`${celula} ${j === 0 ? "pl-5" : ""} ${c.numerica ? "text-right" : ""} whitespace-nowrap`} style={{ fontWeight: 700 }}>
                        {j === 0
                          ? `Total do filtro`
                          : c.id === "produto"
                            ? <span style={{ fontWeight: 400, color: "var(--muted-foreground)" }}>{formatarNumero(filtrados.length)} linhas · {formatarNumero(notasNoFiltro)} notas</span>
                            : c.id === "qtd"
                              ? formatarNumero(totQtd)
                              : c.id === "desc"
                                ? formatarMoeda(totDesc)
                                : c.id === "liq"
                                  ? formatarMoeda(totLiq)
                                  : ""}
                      </td>
                    ))}
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}

        {/* Paginação */}
        <div className="flex items-center justify-between gap-4 flex-wrap px-5 py-3 border-t text-xs" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
          <div className="flex items-center gap-3">
            <span>
              {filtrados.length === 0
                ? "0 registros"
                : `${formatarNumero((paginaAtual - 1) * prefs.tamanho + 1)}–${formatarNumero(Math.min(paginaAtual * prefs.tamanho, filtrados.length))} de ${formatarNumero(filtrados.length)}`}
            </span>
            <span className="inline-flex items-center gap-1.5">
              Por página
              <Select value={String(prefs.tamanho)} onValueChange={(v) => setPrefs((p) => ({ ...p, tamanho: Number(v) }))}>
                <SelectTrigger className="h-7 text-xs w-[76px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[25, 50, 100, 200].map((t) => (
                    <SelectItem key={t} value={String(t)} className="text-xs">
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </span>
          </div>
          <nav className="flex items-center gap-1" aria-label="Paginação">
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual <= 1} onClick={() => setPagina(1)} aria-label="Primeira página">
              <ChevronsLeft size={14} />
            </Button>
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual <= 1} onClick={() => setPagina(paginaAtual - 1)} aria-label="Página anterior">
              <ChevronLeft size={14} />
            </Button>
            {paginasVisiveis(paginaAtual, totalPaginas).map((p, k) =>
              p === "…" ? (
                <span key={`e${k}`} className="px-1">
                  …
                </span>
              ) : (
                <button
                  key={p}
                  onClick={() => setPagina(p)}
                  className="h-7 min-w-7 px-2 rounded-md text-xs"
                  aria-current={p === paginaAtual ? "page" : undefined}
                  style={{
                    background: p === paginaAtual ? "var(--primary)" : "transparent",
                    color: p === paginaAtual ? "#fff" : "var(--foreground)",
                    fontWeight: p === paginaAtual ? 700 : 500,
                  }}
                >
                  {formatarNumero(p)}
                </button>
              ),
            )}
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual >= totalPaginas} onClick={() => setPagina(paginaAtual + 1)} aria-label="Próxima página">
              <ChevronRight size={14} />
            </Button>
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual >= totalPaginas} onClick={() => setPagina(totalPaginas)} aria-label="Última página">
              <ChevronsRight size={14} />
            </Button>
          </nav>
        </div>
      </div>

      {/* Detalhe da nota */}
      <Sheet open={!!notaAberta} onOpenChange={(v) => !v && setNotaAberta(null)}>
        <SheetContent className="w-[520px] sm:max-w-[520px] overflow-y-auto">
          {notaAberta && (
            <>
              <SheetHeader>
                <SheetTitle>Nota {notaAberta.nota}</SheetTitle>
                <SheetDescription>
                  {dataDe(notaAberta)} · {nomeUnidade(notaAberta.loja)} · {notaAberta.cad ? "cliente cadastrado" : "consumidor"} · {notaAberta.pag}
                  {notaAberta.enc ? " · encomenda (fora da previsão)" : ""}
                </SheetDescription>
              </SheetHeader>
              <div className="px-4 pb-6 flex flex-col gap-4">
                <div className="grid grid-cols-3 gap-2">
                  {[
                    ["Itens", formatarNumero(itensNota.length)],
                    ["Quantidade", formatarNumero(itensNota.reduce((s, r) => s + r.qtd, 0))],
                    ["Valor líquido", formatarMoeda(itensNota.reduce((s, r) => s + r.liq, 0))],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                      <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                        {k}
                      </p>
                      <p className="text-sm" style={{ fontWeight: 700 }}>
                        {v}
                      </p>
                    </div>
                  ))}
                </div>
                <table className="w-full text-xs" style={{ fontVariantNumeric: "tabular-nums" }}>
                  <thead>
                    <tr style={{ background: "var(--muted)" }}>
                      <th className="text-left px-2 py-2">Produto</th>
                      <th className="text-right px-2 py-2">Qtd.</th>
                      <th className="text-right px-2 py-2">Unit.</th>
                      <th className="text-right px-2 py-2">Líquido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itensNota.map((r) => (
                      <tr key={r.i} style={{ borderBottom: "1px solid var(--border)", background: r.i === notaAberta.i ? "var(--secondary)" : undefined }}>
                        <td className="px-2 py-2">
                          <p style={{ fontWeight: 500 }}>{r.nome}</p>
                          <p className="inline-flex items-center gap-1" style={{ color: "var(--muted-foreground)" }}>
                            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: COR_CAT[r.cat] }} /> {NOME_CAT[r.cat]} · cód. {r.cod}
                          </p>
                        </td>
                        <td className="px-2 py-2 text-right">{formatarQtd(r.qtd)}</td>
                        <td className="px-2 py-2 text-right whitespace-nowrap">{formatarMoeda(r.unit)}</td>
                        <td className="px-2 py-2 text-right whitespace-nowrap" style={{ fontWeight: 600 }}>
                          {formatarMoeda(r.liq)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                  A linha destacada é a que você clicou. Descontos da nota: {formatarMoeda(itensNota.reduce((s, r) => s + r.desc, 0))}.
                </p>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
