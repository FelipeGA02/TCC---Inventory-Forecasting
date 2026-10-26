import { useLocation } from "react-router";
import { User, RefreshCw, LogOut } from "lucide-react";
import { toast } from "sonner";
import { mensagemDoErro } from "@/lib/http/errors";
import { useAuth } from "../../auth/AuthContext";
import { useDados } from "../../data/CarregarDados";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Notificacoes } from "./Notificacoes";
import { TreinarPrevisoes } from "./TreinarPrevisoes";

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Início", subtitle: "Visão geral das vendas da base: faturamento, mix, clientes e produtos" },
  "/importar": { title: "Carregar Planilha de Vendas", subtitle: "Envie o relatório de vendas e depois treine as previsões" },
  "/pre-visualizacao": { title: "Conferir Dados", subtitle: "Gerencie os dados importados pelas planilhas" },
  "/previsao": { title: "Previsão de Vendas", subtitle: "Previsão diária das categorias e dos produtos de grama de cada loja, e o histórico das previsões" },
  "/exportar": { title: "Relatórios", subtitle: "Escolha, confira a prévia e baixe em Excel, CSV ou PDF" },
};

const NOME_PERFIL = { admin: "Gestora (administração)", viewer: "Gerente (consulta)" } as const;

export function Header() {
  const location = useLocation();
  const info = routeTitles[location.pathname] ?? { title: "FloraManager", subtitle: "" };
  const { usuario, sair } = useAuth();
  const { recarregar, atualizando } = useDados();

  const atualizar = () =>
    recarregar()
      .then(() => toast.success("Dados atualizados."))
      .catch((e: unknown) => toast.error(mensagemDoErro(e)));

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
        <Button
          variant="ghost"
          size="sm"
          className="gap-2 text-xs"
          style={{ color: "var(--muted-foreground)" }}
          onClick={atualizar}
          disabled={atualizando}
        >
          <RefreshCw size={14} className={atualizando ? "animate-spin" : undefined} />
          {atualizando ? "Atualizando..." : "Atualizar"}
        </Button>
        <TreinarPrevisoes />
        <Notificacoes />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{ background: "var(--primary)" }}
              aria-label="Conta e sair"
              title={usuario?.nome}
            >
              <User size={16} color="#fff" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-56">
            {usuario && (
              <DropdownMenuLabel className="flex flex-col gap-0.5">
                <span style={{ fontWeight: 600 }}>{usuario.nome}</span>
                <span className="text-xs" style={{ color: "var(--muted-foreground)", fontWeight: 400 }}>
                  {usuario.email}
                </span>
                <span className="text-xs" style={{ color: "var(--muted-foreground)", fontWeight: 400 }}>
                  {NOME_PERFIL[usuario.perfil]}
                </span>
              </DropdownMenuLabel>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={sair} className="gap-2">
              <LogOut size={14} /> Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
