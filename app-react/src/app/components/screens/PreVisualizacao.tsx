import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Copy, FileSpreadsheet, Rows3, Search, ShieldCheck, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import type { RegistroVenda } from "@/domain/types";
import { CORES_CATEGORIA, categorias, dados, nomeUnidade, unidades } from "../../data/mockData";
import { Kpi, MarcaCategoria, Segmentado } from "../shared";
import { formatarData, formatarMesAno, formatarMoeda, formatarNumero, formatarPercentual, formatarQtd } from "@/lib/format";

const PAGE_SIZE = 15;

type FiltroCat = RegistroVenda["categoria"] | "todas";
type FiltroLojaReg = RegistroVenda["unidade"] | "todas";

const NOME_CATEGORIA: Record<RegistroVenda["categoria"], string> = {
  ...(Object.fromEntries(categorias.map((c) => [c.id, c.nome])) as Record<string, string>),
  "flores-de-corte": "Flores de corte",
} as Record<RegistroVenda["categoria"], string>;

export function PreVisualizacao() {
  const [busca, setBusca] = useState("");
  const [loja, setLoja] = useState<FiltroLojaReg>("todas");
  const [categoria, setCategoria] = useState<FiltroCat>("todas");
  const [pagina, setPagina] = useState(1);

  const registros = dados.registros_amostra;
  const imp = dados.importacao;

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return registros.filter(
      (r) =>
        (loja === "todas" || r.unidade === loja) &&
        (categoria === "todas" || r.categoria === categoria) &&
        (!termo || r.produto.toLowerCase().includes(termo) || r.codigo.includes(termo) || r.documento.includes(termo)),
    );
  }, [registros, busca, loja, categoria]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / PAGE_SIZE));
  const paginaAtual = Math.min(pagina, totalPaginas);
  const paginados = filtrados.slice((paginaAtual - 1) * PAGE_SIZE, paginaAtual * PAGE_SIZE);
  const filtrosAtivos = busca !== "" || loja !== "todas" || categoria !== "todas";

  const mudar = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPagina(1);
  };

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Kpi icone={FileSpreadsheet} rotulo="Planilhas carregadas" valor={imp.arquivos.length}
          detalhe={`${formatarMesAno(imp.arquivos[0]!.competencia)} a ${formatarMesAno(imp.arquivos[imp.arquivos.length - 1]!.competencia)} · uma por mês`} />
        <Kpi icone={Rows3} rotulo="Linhas de venda lidas" valor={formatarNumero(imp.qualidade.linhas_lidas)}
          detalhe={`${formatarNumero(dados.base.linhas)} usadas na previsão (fretes e serviços ficam de fora)`} />
        <Kpi icone={Copy} rotulo="Duplicatas encontradas" valor={imp.qualidade.duplicatas}
          detalhe="Cada planilha tem uma assinatura: carregar a mesma de novo não duplica vendas" />
        <Kpi icone={ShieldCheck} rotulo="Linhas com problema" valor={imp.qualidade.linhas_removidas}
          detalhe={`${imp.qualidade.clientes_sem_nome_corrigidos} vendas sem nome de cliente foram ajustadas`} />
      </div>

      {/* Volume por loja e categoria */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
            O que está na base · {formatarData(dados.base.inicio)} a {formatarData(dados.base.fim)}
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-2 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5">Loja</TableHead>
                <TableHead className="text-xs text-right">Linhas de venda</TableHead>
                <TableHead className="text-xs text-right">Produtos diferentes</TableHead>
                {categorias.map((c) => (
                  <TableHead key={c.id} className="text-xs text-right">
                    <span className="inline-flex items-center gap-1.5">
                      <MarcaCategoria id={c.id} tamanho={8} /> {c.nome}
                    </span>
                  </TableHead>
                ))}
                <TableHead className="text-xs text-right pr-5">Flores de corte</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {unidades.map((u) => {
                const total = u.volume_total + u.volume_flores_de_corte;
                return (
                  <TableRow key={u.id}>
                    <TableCell className="text-xs pl-5" style={{ fontWeight: 600 }}>
                      {u.nome} <span style={{ color: "var(--muted-foreground)", fontWeight: 400 }}>· {u.cidade}</span>
                    </TableCell>
                    <TableCell className="text-xs text-right">{formatarNumero(u.linhas)}</TableCell>
                    <TableCell className="text-xs text-right">{formatarNumero(u.skus_vendidos)}</TableCell>
                    {categorias.map((c) => (
                      <TableCell key={c.id} className="text-xs text-right">
                        {formatarNumero(u.volume_por_categoria[c.id])}{" "}
                        <span style={{ color: "var(--muted-foreground)" }}>({formatarPercentual(u.volume_por_categoria[c.id] / total)})</span>
                      </TableCell>
                    ))}
                    <TableCell className="text-xs text-right pr-5" style={{ color: "var(--muted-foreground)" }}>
                      {formatarNumero(u.volume_flores_de_corte)} ({formatarPercentual(u.volume_flores_de_corte / total)})
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <p className="text-xs px-5 pt-2" style={{ color: "var(--muted-foreground)" }}>
            Quantidades somadas na unidade de venda de cada produto (m², bandeja, saco, unidade). Flores de corte entram na
            previsão da loja, mas não têm painel próprio.
          </p>
        </CardContent>
      </Card>

      {/* Registros */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-4 px-5 flex flex-col gap-3">
          <div>
            <CardTitle className="text-sm" style={{ fontWeight: 600 }}>
              Últimas vendas registradas
            </CardTitle>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
              Os 2 últimos dias com venda em cada loja, como vieram da planilha. O nome do cliente não é exibido.
            </p>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
              <Input
                value={busca}
                onChange={(e) => mudar(setBusca)(e.target.value)}
                placeholder="Produto, código ou nota"
                className="h-8 text-xs pl-8 w-56"
              />
            </div>
            <Segmentado
              rotulo="Loja"
              opcoes={[{ valor: "todas" as FiltroLojaReg, label: "Todas" }, ...unidades.map((u) => ({ valor: u.id as FiltroLojaReg, label: u.nome }))]}
              valor={loja}
              onChange={mudar(setLoja)}
            />
            <Segmentado
              rotulo="Categoria"
              opcoes={[
                { valor: "todas" as FiltroCat, label: "Todas" },
                ...categorias.map((c) => ({ valor: c.id as FiltroCat, label: c.nome })),
                { valor: "flores-de-corte" as FiltroCat, label: "Flores de corte" },
              ]}
              valor={categoria}
              onChange={mudar(setCategoria)}
            />
            {filtrosAtivos && (
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => {
                  setBusca("");
                  setLoja("todas");
                  setCategoria("todas");
                  setPagina(1);
                }}
              >
                <X size={12} /> Limpar
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "var(--muted)" }}>
                <TableHead className="text-xs pl-5">Data</TableHead>
                <TableHead className="text-xs">Loja</TableHead>
                <TableHead className="text-xs">Nota</TableHead>
                <TableHead className="text-xs">Produto</TableHead>
                <TableHead className="text-xs">Categoria</TableHead>
                <TableHead className="text-xs text-right">Qtd.</TableHead>
                <TableHead className="text-xs text-right">Valor</TableHead>
                <TableHead className="text-xs pr-5">Cliente</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginados.map((r, i) => (
                <TableRow key={`${r.documento}-${r.codigo}-${i}`}>
                  <TableCell className="text-xs pl-5 whitespace-nowrap">{formatarData(r.data)}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">{nomeUnidade(r.unidade)}</TableCell>
                  <TableCell className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    {r.documento}
                  </TableCell>
                  <TableCell className="text-xs">
                    <span style={{ fontWeight: 500 }}>{r.produto}</span>
                    <span className="ml-2" style={{ color: "var(--muted-foreground)" }}>
                      {r.codigo}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        className="inline-block w-2 h-2 rounded-sm"
                        style={{ background: r.categoria === "flores-de-corte" ? "#c0c8c2" : CORES_CATEGORIA[r.categoria] }}
                      />
                      {NOME_CATEGORIA[r.categoria]}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-right">{formatarQtd(r.quantidade)}</TableCell>
                  <TableCell className="text-xs text-right whitespace-nowrap">{formatarMoeda(r.valor)}</TableCell>
                  <TableCell className="text-xs pr-5" style={{ color: "var(--muted-foreground)" }}>
                    {r.tipo_cliente}
                  </TableCell>
                </TableRow>
              ))}
              {paginados.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-xs text-center py-8" style={{ color: "var(--muted-foreground)" }}>
                    Nenhuma venda encontrada com esses filtros.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          <div className="flex items-center justify-between px-5 py-3 border-t text-xs" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
            <span>
              {filtrados.length === 0
                ? "0 registros"
                : `${formatarNumero((paginaAtual - 1) * PAGE_SIZE + 1)}–${formatarNumero(Math.min(paginaAtual * PAGE_SIZE, filtrados.length))} de ${formatarNumero(filtrados.length)} registros`}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual <= 1} onClick={() => setPagina(paginaAtual - 1)} aria-label="Página anterior">
                <ChevronLeft size={14} />
              </Button>
              <span>
                Página {paginaAtual} de {totalPaginas}
              </span>
              <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={paginaAtual >= totalPaginas} onClick={() => setPagina(paginaAtual + 1)} aria-label="Próxima página">
                <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
