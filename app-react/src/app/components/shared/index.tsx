import { createContext, useContext, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import type { CategoriaId, FiltroCategoria, FiltroUnidade, StatusModelo } from "@/domain/types";
import { badgeStatus, estiloStatus } from "@/styles/tokens";
import { CORES_CATEGORIA, HORIZONTE_PADRAO, categorias, horizonteEfetivo, lojas, opcoesHorizonte } from "../../data/painel";
import { Card, CardContent } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

// ---------------------------------------------------------------------------
// Filtros de loja, categoria e horizonte compartilhados entre as telas
// ---------------------------------------------------------------------------

interface FiltroLojaCtx {
  unidade: FiltroUnidade;
  setUnidade: (u: FiltroUnidade) => void;
  categoria: FiltroCategoria;
  setCategoria: (c: FiltroCategoria) => void;
  /** Quantos dias à frente as telas de previsão mostram (14 a 91, padrão 14 — ADR-021). */
  horizonte: number;
  setHorizonte: (dias: number) => void;
}

const FiltroLojaContext = createContext<FiltroLojaCtx | null>(null);

export function FiltroLojaProvider({ children }: { children: ReactNode }) {
  const [unidade, setUnidade] = useState<FiltroUnidade>("todas");
  const [categoria, setCategoria] = useState<FiltroCategoria>("todas");
  const [horizonte, setHorizonte] = useState<number>(HORIZONTE_PADRAO);
  return (
    <FiltroLojaContext.Provider value={{ unidade, setUnidade, categoria, setCategoria, horizonte, setHorizonte }}>
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

/** Opções do filtro de loja (lidas do contexto na hora: o módulo é importado antes dele). */
export const opcoesLoja = (): Opcao<FiltroUnidade>[] => [
  { valor: "todas", label: "Todas as lojas" },
  ...lojas.map((u) => ({ valor: u.id as FiltroUnidade, label: u.nome })),
];

export function FiltroLoja() {
  const { unidade, setUnidade } = useFiltroLoja();
  return <Segmentado rotulo="Loja" opcoes={opcoesLoja()} valor={unidade} onChange={setUnidade} />;
}

export const opcoesCategoria = (): Opcao<FiltroCategoria>[] => [
  { valor: "todas", label: "Todas" },
  ...categorias.map((c) => ({ valor: c.id as FiltroCategoria, label: c.nome })),
];

export function FiltroCategoriaGlobal() {
  const { categoria, setCategoria } = useFiltroLoja();
  return <Segmentado rotulo="Categoria" opcoes={opcoesCategoria()} valor={categoria} onChange={setCategoria} />;
}

/** Seletor do horizonte (2 semanas a 3 meses), limitado aos dias que o último treino previu. */
export function FiltroHorizonte({ valor, onChange }: { valor?: number; onChange?: (dias: number) => void } = {}) {
  const ctx = useFiltroLoja();
  const atual = horizonteEfetivo(valor ?? ctx.horizonte);
  const mudar = onChange ?? ctx.setHorizonte;
  const opcoes = opcoesHorizonte();
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-medium" style={{ color: "var(--muted-foreground)" }}>
        Horizonte
      </span>
      <Select value={String(atual)} onValueChange={(v) => mudar(Number(v))}>
        <SelectTrigger aria-label="Horizonte da previsão" className="h-8 text-xs w-44 bg-white" style={{ fontWeight: 600 }}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {opcoes.map((o) => (
            <SelectItem key={o.dias} value={String(o.dias)} className="text-xs" disabled={!o.disponivel}>
              {o.label}
              <span style={{ color: "var(--muted-foreground)", fontWeight: 400 }}>
                {o.disponivel ? ` · ${o.dias} dias` : " · disponível no próximo treino"}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
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

// ---------------------------------------------------------------------------
// Peças visuais
// ---------------------------------------------------------------------------

/** Selo só quando a série não tem previsão (poucos dados, falha, calculando): com previsão, nada. */
export function StatusBadge({ status, compacto = false }: { status: StatusModelo; compacto?: boolean }) {
  if (status === "trained") return null;
  const e = estiloStatus[status];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs whitespace-nowrap"
      style={{ ...badgeStatus(status), fontWeight: 600 }}
      title={compacto ? e.explicacao : undefined}
    >
      <span aria-hidden>•</span>
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
