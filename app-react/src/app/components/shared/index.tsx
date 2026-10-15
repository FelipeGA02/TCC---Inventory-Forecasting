import { createContext, useContext, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import type { CategoriaId, FiltroCategoria, FiltroUnidade, StatusModelo } from "@/domain/types";
import { badgeStatus, estiloStatus } from "@/styles/tokens";
import { CORES_CATEGORIA, categorias, unidades } from "../../data/mockData";
import { Card, CardContent } from "../ui/card";

// ---------------------------------------------------------------------------
// Filtros de loja e categoria compartilhados entre as telas
// ---------------------------------------------------------------------------

interface FiltroLojaCtx {
  unidade: FiltroUnidade;
  setUnidade: (u: FiltroUnidade) => void;
  categoria: FiltroCategoria;
  setCategoria: (c: FiltroCategoria) => void;
}

const FiltroLojaContext = createContext<FiltroLojaCtx | null>(null);

export function FiltroLojaProvider({ children }: { children: ReactNode }) {
  const [unidade, setUnidade] = useState<FiltroUnidade>("todas");
  const [categoria, setCategoria] = useState<FiltroCategoria>("todas");
  return (
    <FiltroLojaContext.Provider value={{ unidade, setUnidade, categoria, setCategoria }}>
      {children}
    </FiltroLojaContext.Provider>
  );
}

export function useFiltroLoja(): FiltroLojaCtx {
  const ctx = useContext(FiltroLojaContext);
  if (!ctx) throw new Error("useFiltroLoja fora do FiltroLojaProvider");
  return ctx;
}

// ---------------------------------------------------------------------------
// Controles segmentados
// ---------------------------------------------------------------------------

interface Opcao<T extends string> {
  valor: T;
  label: string;
}

export function Segmentado<T extends string>({
  opcoes,
  valor,
  onChange,
  rotulo,
}: {
  opcoes: Opcao<T>[];
  valor: T;
  onChange: (v: T) => void;
  rotulo?: string;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {rotulo && (
        <span className="text-xs font-medium" style={{ color: "var(--muted-foreground)" }}>
          {rotulo}
        </span>
      )}
      <div
        role="radiogroup"
        aria-label={rotulo}
        className="inline-flex rounded-lg p-0.5 gap-0.5"
        style={{ background: "var(--muted)" }}
      >
        {opcoes.map((o) => {
          const ativo = o.valor === valor;
          return (
            <button
              key={o.valor}
              role="radio"
              aria-checked={ativo}
              onClick={() => onChange(o.valor)}
              className="px-3 py-1.5 rounded-md text-xs transition-colors"
              style={{
                background: ativo ? "#fff" : "transparent",
                color: ativo ? "var(--primary)" : "var(--muted-foreground)",
                fontWeight: ativo ? 600 : 500,
                boxShadow: ativo ? "0 1px 2px rgba(26,46,30,0.12)" : "none",
              }}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const opcoesLoja: Opcao<FiltroUnidade>[] = [
  { valor: "todas", label: "Todas as lojas" },
  ...unidades.map((u) => ({ valor: u.id as FiltroUnidade, label: u.nome })),
];

export function FiltroLoja() {
  const { unidade, setUnidade } = useFiltroLoja();
  return <Segmentado rotulo="Loja" opcoes={opcoesLoja} valor={unidade} onChange={setUnidade} />;
}

export const opcoesCategoria: Opcao<FiltroCategoria>[] = [
  { valor: "todas", label: "Todas" },
  ...categorias.map((c) => ({ valor: c.id as FiltroCategoria, label: c.nome })),
];

export function FiltroCategoriaGlobal() {
  const { categoria, setCategoria } = useFiltroLoja();
  return <Segmentado rotulo="Categoria" opcoes={opcoesCategoria} valor={categoria} onChange={setCategoria} />;
}

/** Barra de filtros padrão das telas: loja + categoria. */
export function BarraFiltros({ extra }: { extra?: ReactNode }) {
  return (
    <div className="flex items-center gap-x-6 gap-y-3 flex-wrap">
      <FiltroLoja />
      <FiltroCategoriaGlobal />
      {extra}
    </div>
  );
}

/** Interruptor simples (sem dependência extra) para "somente produtos regulares". */
export function Interruptor({ ligado, onChange, rotulo, dica }: { ligado: boolean; onChange: (v: boolean) => void; rotulo: string; dica?: string }) {
  return (
    <label className="inline-flex items-center gap-2 cursor-pointer select-none" title={dica}>
      <button
        type="button"
        role="switch"
        aria-checked={ligado}
        onClick={() => onChange(!ligado)}
        className="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
        style={{ background: ligado ? "var(--primary)" : "#c4ccc6" }}
      >
        <span
          className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
          style={{ left: ligado ? 18 : 2, boxShadow: "0 1px 2px rgba(0,0,0,.2)" }}
        />
      </button>
      <span className="text-xs" style={{ color: "var(--foreground)", fontWeight: 500 }}>
        {rotulo}
      </span>
    </label>
  );
}

/** Selo do tipo de produto: regular (tem previsão própria) ou irregular (só histórico). */
export function SeloRegular({ regular }: { regular: boolean }) {
  return regular ? (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] whitespace-nowrap"
      style={{ background: "#e8f5e0", color: "#1a6b3c", border: "1px solid #b4dbb4", fontWeight: 600 }}
      title="Vende quase todo dia: tem modelo e previsão diária próprios"
    >
      regular
    </span>
  ) : (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] whitespace-nowrap"
      style={{ background: "#f1f3f5", color: "#5a6471", border: "1px solid #d8dce1", fontWeight: 600 }}
      title="Venda esparsa ou irregular: sem previsão diária, só histórico"
    >
      irregular
    </span>
  );
}

// ---------------------------------------------------------------------------
// Peças visuais
// ---------------------------------------------------------------------------

export function StatusBadge({ status, compacto = false }: { status: StatusModelo; compacto?: boolean }) {
  const e = estiloStatus[status];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs whitespace-nowrap"
      style={{ ...badgeStatus(status), fontWeight: 600 }}
      title={compacto ? e.explicacao : undefined}
    >
      <span aria-hidden>{status === "trained" ? "✓" : status === "low_confidence" ? "!" : "•"}</span>
      {e.label}
    </span>
  );
}

export function MarcaCategoria({ id, tamanho = 10 }: { id: CategoriaId; tamanho?: number }) {
  return (
    <span
      aria-hidden
      className="inline-block rounded-sm flex-shrink-0"
      style={{ width: tamanho, height: tamanho, background: CORES_CATEGORIA[id] }}
    />
  );
}

export function LegendaCategorias({ extra }: { extra?: ReactNode }) {
  return (
    <div className="flex items-center gap-4 flex-wrap text-xs" style={{ color: "var(--muted-foreground)" }}>
      {categorias.map((c) => (
        <span key={c.id} className="inline-flex items-center gap-1.5">
          <MarcaCategoria id={c.id} />
          {c.nome}
        </span>
      ))}
      {extra}
    </div>
  );
}

export function Kpi({
  icone: Icone,
  rotulo,
  valor,
  detalhe,
  rodape,
}: {
  icone: LucideIcon;
  rotulo: string;
  valor: ReactNode;
  detalhe?: ReactNode;
  rodape?: ReactNode;
}) {
  return (
    <Card className="border" style={{ borderColor: "var(--border)" }}>
      <CardContent className="p-5 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "var(--secondary)" }}
          >
            <Icone size={16} style={{ color: "var(--primary)" }} />
          </div>
          <p className="text-xs" style={{ color: "var(--muted-foreground)", fontWeight: 500 }}>
            {rotulo}
          </p>
        </div>
        <div className="text-2xl" style={{ color: "var(--foreground)", fontWeight: 700, lineHeight: 1.1 }}>
          {valor}
        </div>
        {detalhe && (
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            {detalhe}
          </p>
        )}
        {rodape}
      </CardContent>
    </Card>
  );
}

export function TituloSecao({ titulo, descricao, acao }: { titulo: string; descricao?: string; acao?: ReactNode }) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h2 className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
          {titulo}
        </h2>
        {descricao && (
          <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
            {descricao}
          </p>
        )}
      </div>
      {acao}
    </div>
  );
}

/** Mini gráfico de barras (8 semanas) em SVG puro — cabe numa célula de tabela. */
export function MiniBarras({ valores, cor }: { valores: number[]; cor: string }) {
  const max = Math.max(...valores, 1);
  const w = 64;
  const h = 20;
  const passo = w / valores.length;
  return (
    <svg width={w} height={h} role="img" aria-label="Vendas das últimas 8 semanas">
      {valores.map((v, i) => {
        const alt = Math.max(1, (v / max) * h);
        return (
          <rect key={i} x={i * passo + 1} y={h - alt} width={passo - 2} height={alt} rx={1} fill={cor} opacity={i === valores.length - 1 ? 1 : 0.55}>
            <title>{`Semana ${i + 1}: ${Math.round(v)}`}</title>
          </rect>
        );
      })}
    </svg>
  );
}
