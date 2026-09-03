import { useState } from "react";
import { CheckCircle2, Clock, Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Label } from "@/app/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/app/components/ui/radio-group";
import { ScrollArea } from "@/app/components/ui/scroll-area";
import { toast } from "sonner";
import { EstadoVazio } from "@/app/components/feedback/EstadoVazio";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";
import { useCatalogo } from "@/features/forecast/hooks";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { useExportacao, useHistoricoRelatorios } from "./hooks";

const GRUPOS = ["Rosas", "Lírios", "Tropicais", "Orquídeas", "Bulbosas", "Crisântemos"];

const PERIODOS = [
  { valor: "junho-2026", label: "Junho 2026" },
  { valor: "maio-2026", label: "Maio 2026" },
  { valor: "q2-2026", label: "Q2 2026" },
  { valor: "h1-2026", label: "1º Sem 2026" },
];

const TIPOS_RELATORIO = [
  {
    id: "previsao",
    nome: "Quanto comprar nas próximas semanas",
    descricao: "Lista de compra recomendada por produto e loja para o período selecionado",
  },
  {
    id: "alertas",
    nome: "Produtos que precisam de reposição",
    descricao: "Todos os itens com estoque baixo, ordenados do mais urgente ao menos urgente",
  },
  {
    id: "desempenho",
    nome: "Qualidade das previsões do sistema",
    descricao: "Indicadores de acerto (MAPE, MAE, RMSE, R²) para cada produto ao longo do tempo",
  },
  {
    id: "cenarios",
    nome: "Resultado das simulações de promoções",
    descricao: "Comparativo de promoções simuladas com impacto estimado em vendas e lucro",
  },
  {
    id: "completo",
    nome: "Relatório completo para gestores",
    descricao: "Visão geral com todas as análises, gráficos e recomendações em um único documento",
  },
];

export function ReportsPage() {
  const [periodo, setPeriodo] = useState("junho-2026");
  const [unidade, setUnidade] = useState("todos");
  const [grupo, setGrupo] = useState("todos");
  const [formato, setFormato] = useState<"pdf" | "xlsx">("pdf");
  const [gerando, setGerando] = useState<string | null>(null);

  const catalogo = useCatalogo();
  const historico = useHistoricoRelatorios();
  const exportacao = useExportacao();

  async function baixar(relatorioId: string, nome: string) {
    setGerando(relatorioId);
    await exportacao.executar({ periodo, unidade, grupo, formato });
    setGerando(null);

    if (exportacao.erro) {
      toast.error(exportacao.erro);
      return;
    }

    historico.recarregar();
    toast.success(`${nome} gerado com sucesso!`, {
      description: `Formato: ${formato.toUpperCase()} · ${new Date().toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })}`,
    });
  }

  return (
    <div className="p-6 flex gap-5 h-full">
      <div className="flex-1 flex flex-col gap-5 min-w-0">
        <Card className="border" style={{ borderColor: cores.borda }}>
          <CardContent className="p-4">
            <div className="grid grid-cols-4 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: cores.textoSuave }}>
                  Período
                </Label>
                <Select value={periodo} onValueChange={setPeriodo}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PERIODOS.map((item) => (
                      <SelectItem key={item.valor} value={item.valor}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: cores.textoSuave }}>
                  Unidade
                </Label>
                <Select value={unidade} onValueChange={setUnidade}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todas</SelectItem>
                    {(catalogo.data?.unidades ?? []).map((item) => (
                      <SelectItem key={item.id} value={item.nome}>
                        {item.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: cores.textoSuave }}>
                  Grupo de Produtos
                </Label>
                <Select value={grupo} onValueChange={setGrupo}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos</SelectItem>
                    {GRUPOS.map((nome) => (
                      <SelectItem key={nome} value={nome}>
                        {nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-xs" style={{ color: cores.textoSuave }}>
                  Formato
                </Label>
                <RadioGroup
                  value={formato}
                  onValueChange={(valor) => setFormato(valor as "pdf" | "xlsx")}
                  className="flex gap-4 h-8 items-center"
                >
                  <div className="flex items-center gap-1.5">
                    <RadioGroupItem value="pdf" id="formato-pdf" />
                    <Label htmlFor="formato-pdf" className="text-xs cursor-pointer">
                      PDF
                    </Label>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <RadioGroupItem value="xlsx" id="formato-xlsx" />
                    <Label htmlFor="formato-xlsx" className="text-xs cursor-pointer">
                      Excel
                    </Label>
                  </div>
                </RadioGroup>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border flex-1" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-3 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Tipos de Relatório Disponíveis
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-3">
            {TIPOS_RELATORIO.map((relatorio) => {
              const emAndamento = gerando === relatorio.id;
              return (
                <div
                  key={relatorio.id}
                  className="flex items-center gap-4 p-4 rounded-lg border"
                  style={{ borderColor: cores.borda, background: cores.fundo }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: "var(--secondary)" }}
                  >
                    <FileText size={18} style={{ color: cores.primaria }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: cores.texto, fontWeight: 500 }}>
                      {relatorio.nome}
                    </p>
                    <p className="text-xs" style={{ color: cores.textoSuave }}>
                      {relatorio.descricao}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant={emAndamento ? "outline" : "default"}
                    className="gap-1.5 text-xs flex-shrink-0"
                    style={emAndamento ? {} : { background: cores.primaria, color: "#fff" }}
                    onClick={() => baixar(relatorio.id, relatorio.nome)}
                    disabled={gerando !== null}
                  >
                    {emAndamento ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        Gerando…
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

      <div className="w-72 flex-shrink-0">
        <Card className="border h-full flex flex-col" style={{ borderColor: cores.borda }}>
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="text-sm" style={{ color: cores.texto, fontWeight: 600 }}>
              Relatórios Recentes
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-4 pb-4 overflow-hidden">
            {historico.erro ? (
              <EstadoErro mensagem={historico.erro} aoTentarNovamente={historico.recarregar} />
            ) : historico.carregando ? (
              <TelaCarregando mensagem="Carregando o histórico…" />
            ) : (historico.data ?? []).length === 0 ? (
              <EstadoVazio
                icone={FileText}
                titulo="Nenhum relatório ainda"
                descricao="Os relatórios que você gerar aparecem aqui."
              />
            ) : (
              <ScrollArea className="h-full">
                <div className="flex flex-col gap-2">
                  {(historico.data ?? []).map((relatorio) => (
                    <div
                      key={relatorio.id}
                      className="p-3 rounded-lg border"
                      style={{ borderColor: cores.borda, background: cores.fundo }}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="flex items-center gap-1.5">
                          {relatorio.formato === "PDF" ? (
                            <FileText size={13} style={{ color: cores.primaria, flexShrink: 0 }} />
                          ) : (
                            <FileSpreadsheet
                              size={13}
                              style={{ color: estiloUrgencia.ok.cor, flexShrink: 0 }}
                            />
                          )}
                          <span className="text-xs font-medium" style={{ color: cores.texto }}>
                            {relatorio.nome}
                          </span>
                        </div>
                        <CheckCircle2
                          size={13}
                          color={estiloUrgencia.ok.cor}
                          className="flex-shrink-0 mt-0.5"
                        />
                      </div>

                      <div className="flex items-center gap-2 text-xs" style={{ color: cores.textoSuave }}>
                        <Clock size={11} />
                        <span>{relatorio.data}</span>
                        <span>·</span>
                        <span>{relatorio.tamanho}</span>
                      </div>
                      <p className="text-xs mt-1" style={{ color: cores.textoSuave }}>
                        por {relatorio.usuario}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
