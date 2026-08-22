import { useState } from "react";
import { XCircle, AlertTriangle, CheckCircle2, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
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
import { toast } from "sonner";
import { alertasReposicao, unidades } from "../../data/mockData";

const grupos = ["Rosas", "Lírios", "Tropicais", "Orquídeas", "Bulbosas", "Crisântemos"];

const urgenciaConfig: Record<string, { label: string; icon: React.ReactNode; badge: React.CSSProperties; row?: React.CSSProperties }> = {
  critico: {
    label: "Crítico",
    icon: <XCircle size={13} color="#d4183d" />,
    badge: { background: "#fff0f3", color: "#d4183d", border: "1px solid #fcc" },
    row: { background: "#fffafb" },
  },
  atencao: {
    label: "Atenção",
    icon: <AlertTriangle size={13} color="#b77800" />,
    badge: { background: "#fff8e1", color: "#b77800", border: "1px solid #ffe0a0" },
    row: { background: "#fffdf4" },
  },
  ok: {
    label: "OK",
    icon: <CheckCircle2 size={13} color="#1a6b3c" />,
    badge: { background: "#e8f5e0", color: "#1a6b3c", border: "1px solid #b4dbb4" },
  },
};

export function AlertasReposicao() {
  const [filtroUnidade, setFiltroUnidade] = useState("todos");
  const [filtroGrupo, setFiltroGrupo] = useState("todos");

  const nomeUnidade = unidades.find((u) => u.id === filtroUnidade)?.nome;

  const filtrados = alertasReposicao.filter((a) => {
    const matchUnidade = filtroUnidade === "todos" || a.unidade === nomeUnidade;
    const matchGrupo = filtroGrupo === "todos" || a.grupo === filtroGrupo;
    return matchUnidade && matchGrupo;
  });

  const criticos = filtrados.filter((a) => a.urgencia === "critico").length;
  const atencao = filtrados.filter((a) => a.urgencia === "atencao").length;
  const ok = filtrados.filter((a) => a.urgencia === "ok").length;

  const handleExport = (format: string) => {
    toast.success(`Lista exportada em ${format}`, {
      description: `${filtrados.length} itens · ${new Date().toLocaleDateString("pt-BR")}`,
    });
  };

  return (
    <div className="p-6 flex flex-col gap-5">
      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Repor com urgência", value: criticos, icon: <XCircle size={20} color="#d4183d" />, bg: "#fff0f3", color: "#d4183d" },
          { label: "Repor em breve", value: atencao, icon: <AlertTriangle size={20} color="#b77800" />, bg: "#fff8e1", color: "#b77800" },
          { label: "Estoque suficiente", value: ok, icon: <CheckCircle2 size={20} color="#1a6b3c" />, bg: "#e8f5e0", color: "#1a6b3c" },
        ].map((kpi) => (
          <Card key={kpi.label} className="border" style={{ borderColor: "var(--border)" }}>
            <CardContent className="p-5 flex items-center gap-4">
              <div
                className="w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: kpi.bg }}
              >
                {kpi.icon}
              </div>
              <div>
                <p className="text-3xl" style={{ color: kpi.color, fontWeight: 700, lineHeight: 1 }}>
                  {kpi.value}
                </p>
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  {kpi.label}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table card */}
      <Card className="border" style={{ borderColor: "var(--border)" }}>
        <CardHeader className="pb-3 pt-5 px-5">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
              Lista de Reposição
            </CardTitle>
            <div className="flex items-center gap-2">
              <Select value={filtroUnidade} onValueChange={setFiltroUnidade}>
                <SelectTrigger className="h-8 text-xs w-36">
                  <SelectValue placeholder="Unidade" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todas unidades</SelectItem>
                  {unidades.map((u) => (
                    <SelectItem key={u.id} value={u.id}>{u.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filtroGrupo} onValueChange={setFiltroGrupo}>
                <SelectTrigger className="h-8 text-xs w-36">
                  <SelectValue placeholder="Grupo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos grupos</SelectItem>
                  {grupos.map((g) => (
                    <SelectItem key={g} value={g}>{g}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                variant="outline"
                className="h-8 gap-1.5 text-xs"
                onClick={() => handleExport("PDF")}
              >
                <Download size={13} />
                PDF
              </Button>
              <Button
                size="sm"
                className="h-8 gap-1.5 text-xs"
                style={{ background: "var(--primary)", color: "#fff" }}
                onClick={() => handleExport("Excel")}
              >
                <Download size={13} />
                Excel
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-0">
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
              {filtrados.map((row) => {
                const cfg = urgenciaConfig[row.urgencia];
                return (
                  <TableRow key={row.id} style={cfg.row}>
                    <TableCell className="text-xs pl-5" style={{ color: "var(--foreground)", fontWeight: 500 }}>
                      {row.produto}
                    </TableCell>
                    <TableCell className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                      {row.grupo}
                    </TableCell>
                    <TableCell className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                      {row.unidade}
                    </TableCell>
                    <TableCell
                      className="text-xs text-right"
                      style={{
                        color: row.urgencia === "critico" ? "#d4183d" : "var(--foreground)",
                        fontWeight: 600,
                      }}
                    >
                      {row.estoqueAtual}
                    </TableCell>
                    <TableCell className="text-xs text-right" style={{ color: "var(--muted-foreground)" }}>
                      {row.estoqueMinimo}
                    </TableCell>
                    <TableCell className="text-xs text-right" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                      {row.qtdRecomendada > 0 ? row.qtdRecomendada : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-center" style={{ color: "var(--muted-foreground)" }}>
                      {row.prazo}
                    </TableCell>
                    <TableCell className="text-xs text-center pr-5">
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                        style={cfg.badge}
                      >
                        {cfg.icon}
                        {cfg.label}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
