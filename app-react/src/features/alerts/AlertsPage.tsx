import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Download, PackageCheck, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";
import { toast } from "sonner";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { EstadoVazio } from "@/app/components/feedback/EstadoVazio";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { useExportacao } from "@/features/reports/hooks";
import { formatarNumero, pluralizar } from "@/lib/format";
import { cores, estiloUrgencia } from "@/styles/tokens";
import type { Urgencia } from "@/domain/types";
import { BadgeUrgencia, fundoLinha } from "./components/BadgeUrgencia";
import { useAlertas } from "./hooks";

const UNIDADES = ["Centro", "Jardim Canadá", "Itabirito"];
const GRUPOS = ["Rosas", "Lírios", "Tropicais", "Orquídeas", "Bulbosas", "Crisântemos"];

const RESUMO: { urgencia: Urgencia; label: string; icone: typeof XCircle }[] = [
  { urgencia: "critico", label: "Repor com urgência", icone: XCircle },
  { urgencia: "atencao", label: "Repor em breve", icone: AlertTriangle },
  { urgencia: "ok", label: "Estoque suficiente", icone: CheckCircle2 },
];

export function AlertsPage() {
  const [unidade, setUnidade] = useState("todos");
  const [grupo, setGrupo] = useState("todos");

  const filtro = useMemo(() => ({ unidade, grupo }), [unidade, grupo]);
  const { alertas, contagem, carregando, erro, recarregar } = useAlertas(filtro);
  const exportacao = useExportacao();

  async function exportar(formato: "pdf" | "xlsx") {
    await exportacao.executar({ periodo: "atual", unidade, grupo, formato });
    if (exportacao.erro) {
      toast.error(exportacao.erro);
      return;
    }
    toast.success(`Lista exportada em ${formato === "pdf" ? "PDF" : "Excel"}`, {
      description: `${pluralizar(alertas.length, "item", "itens")} · ${new Date().toLocaleDateString("pt-BR")}`,
    });
  }

  if (erro) return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;

  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-4">
        {RESUMO.map(({ urgencia, label, icone: Icone }) => {
          const estilo = estiloUrgencia[urgencia];
          return (
            <Card key={urgencia} className="border" style={{ borderColor: cores.borda }}>
              <CardContent className="p-5 flex items-center gap-4">
                <div
                  className="w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: estilo.fundo }}
                >
                  <Icone size={20} color={estilo.cor} />
                </div>
                <div>
                  <p className="text-3xl" style={{ color: estilo.cor, fontWeight: 700, lineHeight: 1 }}>
                    {carregando ? "—" : formatarNumero(contagem[urgencia])}
                  </p>
                  <p className="text-sm" style={{ color: cores.textoSuave }}>
                    {label}
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="border" style={{ borderColor: cores.borda }}>
        <CardHeader className="pb-3 pt-5 px-5">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Lista de Reposição
            </CardTitle>

            <div className="flex items-center gap-2">
              <Select value={unidade} onValueChange={setUnidade}>
                <SelectTrigger className="h-8 text-xs w-36">
                  <SelectValue placeholder="Unidade" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todas unidades</SelectItem>
                  {UNIDADES.map((nome) => (
                    <SelectItem key={nome} value={nome}>
                      {nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={grupo} onValueChange={setGrupo}>
                <SelectTrigger className="h-8 text-xs w-36">
                  <SelectValue placeholder="Grupo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos grupos</SelectItem>
                  {GRUPOS.map((nome) => (
                    <SelectItem key={nome} value={nome}>
                      {nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                size="sm"
                variant="outline"
                className="h-8 gap-1.5 text-xs"
                disabled={exportacao.emAndamento || alertas.length === 0}
                onClick={() => exportar("pdf")}
              >
                <Download size={13} />
                PDF
              </Button>
              <Button
                size="sm"
                className="h-8 gap-1.5 text-xs"
                style={{ background: cores.primaria, color: "#fff" }}
                disabled={exportacao.emAndamento || alertas.length === 0}
                onClick={() => exportar("xlsx")}
              >
                <Download size={13} />
                Excel
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-0 pb-0">
          {carregando ? (
            <TelaCarregando mensagem="Carregando a lista de reposição…" />
          ) : alertas.length === 0 ? (
            <EstadoVazio
              icone={PackageCheck}
              titulo="Nenhum produto para repor"
              descricao="Com os filtros escolhidos, todo o estoque está acima do mínimo."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow style={{ background: "var(--muted)" }}>
                  <TableHead className="text-xs pl-5">Produto</TableHead>
                  <TableHead className="text-xs">Categoria</TableHead>
                  <TableHead className="text-xs">Loja</TableHead>
                  <TableHead className="text-xs text-right">Em estoque</TableHead>
                  <TableHead className="text-xs text-right">Mínimo aceitável</TableHead>
                  <TableHead className="text-xs text-right">Comprar agora</TableHead>
                  <TableHead className="text-xs text-center">Repor em</TableHead>
                  <TableHead className="text-xs text-center pr-5">Situação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alertas.map((alerta) => (
                  <TableRow key={alerta.id} style={{ background: fundoLinha[alerta.urgencia] }}>
                    <TableCell className="text-xs pl-5" style={{ color: cores.texto, fontWeight: 500 }}>
                      {alerta.produto}
                    </TableCell>
                    <TableCell className="text-xs" style={{ color: cores.textoSuave }}>
                      {alerta.grupo}
                    </TableCell>
                    <TableCell className="text-xs" style={{ color: cores.textoSuave }}>
                      {alerta.unidade}
                    </TableCell>
                    <TableCell
                      className="text-xs text-right"
                      style={{
                        color: alerta.urgencia === "critico" ? estiloUrgencia.critico.cor : cores.texto,
                        fontWeight: 600,
                      }}
                    >
                      {formatarNumero(alerta.estoqueAtual)}
                    </TableCell>
                    <TableCell className="text-xs text-right" style={{ color: cores.textoSuave }}>
                      {formatarNumero(alerta.estoqueMinimo)}
                    </TableCell>
                    <TableCell className="text-xs text-right" style={{ color: cores.texto, fontWeight: 600 }}>
                      {alerta.qtdRecomendada > 0 ? formatarNumero(alerta.qtdRecomendada) : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-center" style={{ color: cores.textoSuave }}>
                      {alerta.prazo}
                    </TableCell>
                    <TableCell className="text-xs text-center pr-5">
                      <BadgeUrgencia urgencia={alerta.urgencia} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
