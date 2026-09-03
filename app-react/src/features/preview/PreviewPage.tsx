import { useState } from "react";
import { ChevronLeft, ChevronRight, Search, SlidersHorizontal, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { EstadoVazio } from "@/app/components/feedback/EstadoVazio";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { useCatalogo } from "@/features/forecast/hooks";
import { formatarNumero } from "@/lib/format";
import { cores } from "@/styles/tokens";
import { filtrosVazios, useRegistrosImportados, type FiltrosPreview } from "./hooks";

export function PreviewPage() {
  const [filtros, setFiltros] = useState<FiltrosPreview>(filtrosVazios);
  const catalogo = useCatalogo();
  const { registros, total, pagina, totalPaginas, porPagina, irPara, carregando, erro, recarregar } =
    useRegistrosImportados(filtros);

  function definirFiltro(campo: keyof FiltrosPreview, valor: string) {
    setFiltros((anterior) => ({ ...anterior, [campo]: valor }));
    irPara(1);
  }

  function limparFiltros() {
    setFiltros(filtrosVazios);
    irPara(1);
  }

  const temFiltro =
    filtros.busca !== "" || filtros.produto !== "todos" || filtros.unidade !== "todos";

  const inicio = total === 0 ? 0 : (pagina - 1) * porPagina + 1;
  const fim = Math.min(pagina * porPagina, total);

  if (erro) return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  if (carregando) return <TelaCarregando mensagem="Carregando os dados enviados…" />;

  const resumo = [
    { label: "Registros no filtro", valor: total },
    { label: "Produtos", valor: catalogo.data?.produtos.length ?? 0 },
    { label: "Unidades", valor: catalogo.data?.unidades.length ?? 0 },
  ];

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-4">
        {resumo.map((item) => (
          <Card key={item.label} className="border" style={{ borderColor: cores.borda }}>
            <CardContent className="p-5">
              <p className="text-2xl" style={{ color: cores.texto, fontWeight: 700, lineHeight: 1 }}>
                {formatarNumero(item.valor)}
              </p>
              <p className="text-sm mt-1" style={{ color: cores.textoSuave }}>
                {item.label}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border" style={{ borderColor: cores.borda }}>
        <CardHeader className="pb-0 pt-5 px-5">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Dados do arquivo enviado
            </CardTitle>
            {temFiltro && (
              <button
                type="button"
                onClick={limparFiltros}
                className="flex items-center gap-1 text-xs"
                style={{ color: cores.textoSuave }}
              >
                <X size={12} />
                Limpar filtros
              </button>
            )}
          </div>
        </CardHeader>

        <div
          className="mx-5 mt-4 mb-1 p-3 rounded-lg flex items-center gap-3 flex-wrap"
          style={{ background: "var(--muted)", border: `1px solid ${cores.borda}` }}
        >
          <SlidersHorizontal size={14} style={{ color: cores.textoSuave, flexShrink: 0 }} />

          <div className="relative flex-1 min-w-48">
            <Search
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: cores.textoSuave }}
            />
            <Input
              value={filtros.busca}
              onChange={(evento) => definirFiltro("busca", evento.target.value)}
              placeholder="Buscar por produto, unidade ou data…"
              className="h-8 pl-8 text-xs bg-white"
              style={{ borderColor: cores.borda }}
              aria-label="Buscar registros"
            />
          </div>

          <div className="w-px h-5" style={{ background: cores.borda }} />

          <div className="flex items-center gap-2">
            <span className="text-xs whitespace-nowrap" style={{ color: cores.textoSuave }}>
              Produto
            </span>
            <Select value={filtros.produto} onValueChange={(valor) => definirFiltro("produto", valor)}>
              <SelectTrigger className="h-8 text-xs w-44 bg-white" style={{ borderColor: cores.borda }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                {(catalogo.data?.produtos ?? []).map((produto) => (
                  <SelectItem key={produto.id} value={produto.nome}>
                    {produto.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs whitespace-nowrap" style={{ color: cores.textoSuave }}>
              Unidade
            </span>
            <Select value={filtros.unidade} onValueChange={(valor) => definirFiltro("unidade", valor)}>
              <SelectTrigger className="h-8 text-xs w-36 bg-white" style={{ borderColor: cores.borda }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todas</SelectItem>
                {(catalogo.data?.unidades ?? []).map((unidade) => (
                  <SelectItem key={unidade.id} value={unidade.nome}>
                    {unidade.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <CardContent className="px-0 pb-0 mt-3">
          {total === 0 ? (
            <EstadoVazio
              icone={Search}
              titulo="Nenhum registro encontrado"
              descricao={
                temFiltro
                  ? "Nenhuma linha casa com os filtros escolhidos. Limpe os filtros para ver tudo."
                  : "Nenhum dado foi enviado ainda. Carregue uma planilha para começar."
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow style={{ background: "var(--muted)" }}>
                    <TableHead className="text-xs pl-5">Data</TableHead>
                    <TableHead className="text-xs">Produto</TableHead>
                    <TableHead className="text-xs">Unidade</TableHead>
                    <TableHead className="text-xs text-right pr-5">Quantidade</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {registros.map((registro) => (
                    <TableRow key={registro.id}>
                      <TableCell className="text-xs pl-5" style={{ color: cores.textoSuave }}>
                        {registro.data}
                      </TableCell>
                      <TableCell className="text-xs" style={{ color: cores.texto, fontWeight: 500 }}>
                        {registro.produto}
                      </TableCell>
                      <TableCell className="text-xs" style={{ color: cores.textoSuave }}>
                        {registro.unidade}
                      </TableCell>
                      <TableCell
                        className="text-xs text-right pr-5 tabular-nums"
                        style={{ color: cores.texto, fontWeight: 500 }}
                      >
                        {formatarNumero(registro.quantidade)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <div
                className="flex items-center justify-between px-5 py-3 border-t"
                style={{ borderColor: cores.borda }}
              >
                <span className="text-xs" style={{ color: cores.textoSuave }}>
                  {formatarNumero(total)} registros · mostrando {inicio}–{fim}
                </span>

                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={pagina === 1}
                    onClick={() => irPara(1)}
                    title="Primeira página"
                  >
                    <ChevronLeft size={14} className="-mr-1" />
                    <ChevronLeft size={14} className="-ml-1" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={pagina === 1}
                    onClick={() => irPara(pagina - 1)}
                    title="Página anterior"
                  >
                    <ChevronLeft size={14} />
                  </Button>

                  <span className="text-xs px-2" style={{ color: cores.texto }}>
                    {pagina} / {totalPaginas}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={pagina >= totalPaginas}
                    onClick={() => irPara(pagina + 1)}
                    title="Próxima página"
                  >
                    <ChevronRight size={14} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    disabled={pagina >= totalPaginas}
                    onClick={() => irPara(totalPaginas)}
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
