import { useLocation } from "react-router";
import { User, RefreshCw } from "lucide-react";
import { Button } from "../ui/button";
import { Notificacoes } from "./Notificacoes";

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Início", subtitle: "Visão geral das vendas da base: faturamento, mix, clientes e produtos" },
  "/importar": { title: "Carregar Planilha de Vendas", subtitle: "Envie o relatório mensal de vendas para atualizar as previsões" },
  "/pre-visualizacao": { title: "Conferir Dados", subtitle: "Gerencie os dados importados pelas planilhas" },
  "/previsao": { title: "Previsão de Vendas", subtitle: "Previsão diária por loja, categoria e produto, e como ela foi testada" },
  "/exportar": { title: "Relatórios", subtitle: "Escolha, confira a prévia e baixe em Excel, CSV ou PDF" },
};

export function Header() {
  const location = useLocation();
  const info = routeTitles[location.pathname] ?? { title: "FloraManager", subtitle: "" };

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b bg-white" style={{ borderColor: "var(--border)" }}>
      <div>
        <h1 className="text-base" style={{ color: "var(--foreground)", fontWeight: 600, lineHeight: "1.3" }}>
          {info.title}
        </h1>
        <p className="text-xs" style={{ color: "var(--muted-foreground)", lineHeight: "1.3" }}>
          {info.subtitle}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="gap-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
          <RefreshCw size={14} />
          Atualizar
        </Button>
        <Notificacoes />
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: "var(--primary)" }}
        >
          <User size={16} color="#fff" />
        </div>
      </div>
    </header>
  );
}
