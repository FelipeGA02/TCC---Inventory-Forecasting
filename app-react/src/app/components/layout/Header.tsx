import { useLocation } from "react-router";
import { Bell, User, RefreshCw } from "lucide-react";
import { Button } from "../ui/button";

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Início", subtitle: "Resumo geral das vendas e previsões de hoje" },
  "/importar": { title: "Carregar Planilha de Vendas", subtitle: "Envie os dados de vendas para atualizar as previsões" },
  "/pre-visualizacao": { title: "Conferir Dados Enviados", subtitle: "Verifique se os dados estão corretos antes de calcular" },
  "/previsao": { title: "Previsão de Compras", subtitle: "Veja quanto comprar de cada produto nas próximas semanas" },
  "/simulador": { title: "Simular Promoções", subtitle: "Veja o impacto estimado de descontos e ofertas especiais" },
  "/exportar": { title: "Baixar Relatórios", subtitle: "Gere e salve relatórios em PDF ou Excel" },
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
        <button
          className="relative w-9 h-9 rounded-lg flex items-center justify-center hover:opacity-80 transition-colors"
          style={{ background: "var(--muted)" }}
        >
          <Bell size={16} style={{ color: "var(--muted-foreground)" }} />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ background: "var(--destructive)" }}
          />
        </button>
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
