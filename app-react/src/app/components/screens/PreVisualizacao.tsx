import { useState, useMemo } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  X,
  SlidersHorizontal,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  tabelaPreVisualizacao,
  produtos,
  unidades,
} from "../../data/mockData";

const PAGE_SIZE = 10;

const filtrosVazios = {
  busca: "",
  produto: "todos",
  unidade: "todos",
};

export function PreVisualizacao() {
  const [filtros, setFiltros] = useState(filtrosVazios);
  const [pagina, setPagina] = useState(1);

  const setFiltro = (
    campo: keyof typeof filtrosVazios,
    valor: string,
  ) => {
    setFiltros((prev) => ({ ...prev, [campo]: valor }));
    setPagina(1);
  };

  const limparFiltros = () => {
    setFiltros(filtrosVazios);
    setPagina(1);
  };

  const filtrosAtivos =
    filtros.busca !== "" ||
    filtros.produto !== "todos" ||
    filtros.unidade !== "todos";

  const filtrados = useMemo(() => {
    const nomeProduto = produtos.find(
      (p) => p.id === filtros.produto,
    )?.nome;
    const nomeUnidade = unidades.find(
      (u) => u.id === filtros.unidade,
    )?.nome;

    return tabelaPreVisualizacao.filter((r) => {
      const matchBusca =
        filtros.busca === "" ||
        r.produto
          .toLowerCase()
          .includes(filtros.busca.toLowerCase()) ||
        r.unidade
          .toLowerCase()
          .includes(filtros.busca.toLowerCase()) ||
        r.data.includes(filtros.busca);
      const matchProduto =
        filtros.produto === "todos" ||
        r.produto === nomeProduto;
      const matchUnidade =
        filtros.unidade === "todos" ||
        r.unidade === nomeUnidade;
      return matchBusca && matchProduto && matchUnidade;
    });
  }, [filtros]);

  const totalPaginas = Math.ceil(filtrados.length / PAGE_SIZE);
  const paginaAtual = Math.min(
    pagina,
    Math.max(1, totalPaginas),
  );
  const paginados = filtrados.slice(
    (paginaAtual - 1) * PAGE_SIZE,
    paginaAtual * PAGE_SIZE,
  );

  const inicio =
    filtrados.length === 0
      ? 0
      : (paginaAtual - 1) * PAGE_SIZE + 1;
  const fim = Math.min(
    paginaAtual * PAGE_SIZE,
    filtrados.length,
  );

  return (
    <div className="p-6 flex flex-col gap-5">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            label: "Total de registros",
            value: tabelaPreVisualizacao.length,
          },
          { label: "Produtos", value: produtos.length },
          { label: "Unidades", value: unidades.length },
        ].map((stat) => (
          <Card
            key={stat.label}
            className="border"
            style={{ borderColor: "var(--border)" }}
          >
            <CardContent className="p-5">
              <p
                className="text-2xl"
                style={{
                  color: "var(--foreground)",
                  fontWeight: 700,
                  lineHeight: 1,
                }}
              >
                {stat.value}
              </p>
              <p
                className="text-sm mt-1"
                style={{ color: "var(--muted-foreground)" }}
              >
                {stat.label}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table card */}
      <Card
        className="border"
        style={{ borderColor: "var(--border)" }}
      >
        {/* Card header */}
        <CardHeader className="pb-0 pt-5 px-5">
          <div className="flex items-center justify-between">
            <CardTitle
              className="text-sm"
              style={{
                color: "var(--foreground)",
                fontWeight: 600,
              }}
            >
              Dados do arquivo enviado
            </CardTitle>
            {filtrosAtivos && (
              <button
                onClick={limparFiltros}
                className="flex items-center gap-1 text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                <X size={12} />
                Limpar filtros
              </button>
            )}
          </div>
        </CardHeader>

        {/* Filter bar */}
        <div
          className="mx-5 mt-4 mb-1 p-3 rounded-lg flex items-center gap-3 flex-wrap"
          style={{
            background: "var(--muted)",
            border: "1px solid var(--border)",
          }}
        >
          <SlidersHorizontal
            size={14}
            style={{
              color: "var(--muted-foreground)",
              flexShrink: 0,
            }}
          />

          {/* Free text search */}
          <div className="relative flex-1 min-w-48">
            <Search
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: "var(--muted-foreground)" }}
            />
            <Input
              value={filtros.busca}
              onChange={(e) =>
                setFiltro("busca", e.target.value)
              }
              placeholder="Buscar por produto, unidade ou data…"
              className="h-8 pl-8 text-xs bg-white"
              style={{ borderColor: "var(--border)" }}
            />
          </div>

          {/* Divider */}
          <div
            className="w-px h-5"
            style={{ background: "var(--border)" }}
          />

          {/* Product select */}
          <div className="flex items-center gap-2">
            <span
              className="text-xs whitespace-nowrap"
              style={{ color: "var(--muted-foreground)" }}
            >
              Produto
            </span>
            <Select
              value={filtros.produto}
              onValueChange={(v) => setFiltro("produto", v)}
            >
              <SelectTrigger
                className="h-8 text-xs w-44 bg-white"
                style={{ borderColor: "var(--border)" }}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                {produtos.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Unit select */}
          <div className="flex items-center gap-2">
            <span
              className="text-xs whitespace-nowrap"
              style={{ color: "var(--muted-foreground)" }}
            >
              Unidade
            </span>
            <Select
              value={filtros.unidade}
              onValueChange={(v) => setFiltro("unidade", v)}
            >
              <SelectTrigger
                className="h-8 text-xs w-36 bg-white"
                style={{ borderColor: "var(--border)" }}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todas</SelectItem>
                {unidades.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <CardContent className="px-0 pb-0 mt-3">
          {filtrados.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-16 gap-2"
              style={{ color: "var(--muted-foreground)" }}
            >
              <Search size={24} strokeWidth={1.5} />
              <p className="text-sm">
                Nenhum registro encontrado.
              </p>
              {filtrosAtivos && (
                <button
                  onClick={limparFiltros}
                  className="text-xs underline underline-offset-2 mt-1"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Limpar filtros
                </button>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow
                    style={{ background: "var(--muted)" }}
                  >
                    <TableHead className="text-xs pl-5">
                      Data
                    </TableHead>
                    <TableHead className="text-xs">
                      Produto
                    </TableHead>
                    <TableHead className="text-xs">
                      Unidade
                    </TableHead>
                    <TableHead className="text-xs text-right pr-5">
                      Quantidade
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginados.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell
                        className="text-xs pl-5"
                        style={{
                          color: "var(--muted-foreground)",
                        }}
                      >
                        {row.data}
                      </TableCell>
                      <TableCell
                        className="text-xs"
                        style={{
                          color: "var(--foreground)",
                          fontWeight: 500,
                        }}
                      >
                        {row.produto}
                      </TableCell>
                      <TableCell
                        className="text-xs"
                        style={{
                          color: "var(--muted-foreground)",
                        }}
                      >
                        {row.unidade}
                      </TableCell>
                      <TableCell
                        className="text-xs text-right pr-5 tabular-nums"
                        style={{
                          color: "var(--foreground)",
                          fontWeight: 500,
                        }}
                      >
                        {row.quantidade.toLocaleString("pt-BR")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div
                className="flex items-center justify-between px-5 py-3 border-t"
                style={{ borderColor: "var(--border)" }}
              >
                <span
                  className="text-xs"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  {filtrosAtivos
                    ? `${filtrados.length} de ${tabelaPreVisualizacao.length} registros`
                    : `${filtrados.length} registros`}
                  {filtrados.length > 0 &&
                    ` · mostrando ${inicio}–${fim}`}
                </span>

                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={paginaAtual === 1}
                    onClick={() => setPagina(1)}
                    title="Primeira página"
                  >
                    <ChevronLeft size={14} className="-mr-1" />
                    <ChevronLeft size={14} className="-ml-1" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={paginaAtual === 1}
                    onClick={() => setPagina((p) => p - 1)}
                  >
                    <ChevronLeft size={14} />
                  </Button>

                  <span
                    className="text-xs px-2"
                    style={{ color: "var(--foreground)" }}
                  >
                    {paginaAtual} / {totalPaginas || 1}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={paginaAtual >= totalPaginas}
                    onClick={() => setPagina((p) => p + 1)}
                  >
                    <ChevronRight size={14} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={paginaAtual >= totalPaginas}
                    onClick={() => setPagina(totalPaginas)}
                    title="Última página"
                  >
                    <ChevronRight size={14} className="-mr-1" />
                    <ChevronRight size={14} className="-ml-1" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}