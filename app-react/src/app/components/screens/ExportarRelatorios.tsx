import { useState } from "react";
import { Download, FileText, Clock, CheckCircle2, FileSpreadsheet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Label } from "../ui/label";
import { RadioGroup, RadioGroupItem } from "../ui/radio-group";
import { ScrollArea } from "../ui/scroll-area";
import { toast } from "sonner";
import { unidades, historicoRelatorios } from "../../data/mockData";

const grupos = ["Rosas", "Lírios", "Tropicais", "Orquídeas", "Bulbosas", "Crisântemos"];

const tiposRelatorio = [
  {
    id: "previsao",
    nome: "Quanto comprar nas próximas semanas",
    desc: "Lista de compra recomendada por produto e loja para o período selecionado",
    icon: FileText,
  },
  {
    id: "desempenho",
    nome: "Qualidade das previsões do sistema",
    desc: "Indicadores de acerto (MAPE, MAE, RMSE, R²) para cada produto ao longo do tempo",
    icon: FileText,
  },
  {
    id: "cenarios",
    nome: "Resultado das simulações de promoções",
    desc: "Comparativo de promoções simuladas com impacto estimado em vendas e lucro",
    icon: FileText,
  },
  {
    id: "completo",
    nome: "Relatório completo para gestores",
    desc: "Visão geral com todas as análises, gráficos e recomendações em um único documento",
    icon: FileText,
  },
];

export function ExportarRelatorios() {
  const [periodo, setPeriodo] = useState("junho-2026");
  const [unidade, setUnidade] = useState("todos");
  const [grupo, setGrupo] = useState("todos");
  const [formato, setFormato] = useState("pdf");
  const [baixando, setBaixando] = useState<string | null>(null);

  const handleDownload = (relatorioId: string, nome: string) => {
    setBaixando(relatorioId);
    setTimeout(() => {
      setBaixando(null);
      toast.success(`${nome} gerado com sucesso!`, {
        description: `Formato: ${formato.toUpperCase()} · ${new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })}`,
      });
    }, 1400);
  };

  return (
    <div className="p-6 flex gap-5 h-full">
      {/* Main content */}
      <div className="flex-1 flex flex-col gap-5 min-w-0">
        {/* Filters */}
        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-4">
            <div className="grid grid-cols-4 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: "var(--muted-foreground)" }}>Período</Label>
                <Select value={periodo} onValueChange={setPeriodo}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="junho-2026">Junho 2026</SelectItem>
                    <SelectItem value="maio-2026">Maio 2026</SelectItem>
                    <SelectItem value="q2-2026">Q2 2026</SelectItem>
                    <SelectItem value="h1-2026">1º Sem 2026</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: "var(--muted-foreground)" }}>Unidade</Label>
                <Select value={unidade} onValueChange={setUnidade}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todas</SelectItem>
                    {unidades.map((u) => (
                      <SelectItem key={u.id} value={u.id}>{u.nome}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: "var(--muted-foreground)" }}>Grupo de Produtos</Label>
                <Select value={grupo} onValueChange={setGrupo}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos</SelectItem>
                    {grupos.map((g) => (
                      <SelectItem key={g} value={g}>{g}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: "var(--muted-foreground)" }}>Formato</Label>
                <RadioGroup
                  value={formato}
                  onValueChange={setFormato}
                  className="flex gap-4 h-8 items-center"
                >
                  <div className="flex items-center gap-1.5">
                    <RadioGroupItem value="pdf" id="pdf" />
                    <Label htmlFor="pdf" className="text-xs cursor-pointer">PDF</Label>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <RadioGroupItem value="excel" id="excel" />
                    <Label htmlFor="excel" className="text-xs cursor-pointer">Excel</Label>
                  </div>
                </RadioGroup>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Report list */}
        <Card className="border flex-1" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-3 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
              Tipos de Relatório Disponíveis
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-3">
            {tiposRelatorio.map((rel) => {
              const Icon = rel.icon;
              const isLoading = baixando === rel.id;
              return (
                <div
                  key={rel.id}
                  className="flex items-center gap-4 p-4 rounded-lg border"
                  style={{ borderColor: "var(--border)", background: "var(--background)" }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: "var(--secondary)" }}
                  >
                    <Icon size={18} style={{ color: "var(--primary)" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: "var(--foreground)", fontWeight: 500 }}>
                      {rel.nome}
                    </p>
                    <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                      {rel.desc}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant={isLoading ? "outline" : "default"}
                    className="gap-1.5 text-xs flex-shrink-0"
                    style={isLoading ? {} : { background: "var(--primary)", color: "#fff" }}
                    onClick={() => handleDownload(rel.id, rel.nome)}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <span className="animate-spin">⟳</span>
                        Gerando...
                      </>
                    ) : (
                      <>
                        <Download size={13} />
                        Baixar {formato.toUpperCase()}
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Sidebar — history */}
      <div className="w-72 flex-shrink-0">
        <Card className="border h-full flex flex-col" style={{ borderColor: "var(--border)" }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: "var(--foreground)", fontWeight: 600 }}>
              Relatórios Recentes
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-4 pb-4 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="flex flex-col gap-2">
                {historicoRelatorios.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-3 rounded-lg border"
                    style={{ borderColor: "var(--border)", background: "var(--background)" }}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5">
                        {rel.formato === "PDF" ? (
                          <FileText size={13} style={{ color: "var(--primary)", flexShrink: 0 }} />
                        ) : (
                          <FileSpreadsheet size={13} style={{ color: "#1a6b3c", flexShrink: 0 }} />
                        )}
                        <span className="text-xs font-medium" style={{ color: "var(--foreground)" }}>
                          {rel.nome}
                        </span>
                      </div>
                      <CheckCircle2 size={13} color="#1a6b3c" className="flex-shrink-0 mt-0.5" />
                    </div>
                    <div className="flex items-center gap-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
                      <Clock size={11} />
                      <span>{rel.data}</span>
                      <span>·</span>
                      <span>{rel.tamanho}</span>
                    </div>
                    <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                      por {rel.usuario}
                    </p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
