import { dados } from "../../data/mockData";
import { formatarData } from "@/lib/format";
import { NavLink } from "react-router";
import {
  LayoutDashboard,
  Upload,
  Table2,
  TrendingUp,
  ShieldCheck,
  FileDown,
  Flower2,
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Início" },
  { to: "/importar", icon: Upload, label: "Carregar Planilha" },
  {
    to: "/pre-visualizacao",
    icon: Table2,
    label: "Conferir Dados",
  },
  {
    to: "/previsao",
    icon: TrendingUp,
    label: "Previsão de Vendas",
  },
  {
    to: "/acerto",
    icon: ShieldCheck,
    label: "Acerto das Previsões",
  },
  {
    to: "/exportar",
    icon: FileDown,
    label: "Relatórios",
  },
];

export function Sidebar() {
  return (
    <aside
      className="w-60 min-h-screen flex flex-col"
      style={{ background: "var(--sidebar)" }}
    >
      <div
        className="flex items-center gap-3 px-5 py-5 border-b"
        style={{ borderColor: "var(--sidebar-border)" }}
      >
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: "var(--sidebar-primary)" }}
        >
          <Flower2 size={20} color="#fff" />
        </div>
        <div>
          <p
            className="text-sm leading-tight"
            style={{
              color: "var(--sidebar-foreground)",
              fontWeight: 600,
            }}
          >
            Verde Perto
          </p>
          <p
            className="text-xs"
            style={{ color: "rgba(232,245,224,0.55)" }}
          >
            Sistema de Previsão
          </p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? "font-medium" : "hover:opacity-80"
              }`
            }
            style={({ isActive }) => ({
              background: isActive
                ? "var(--sidebar-accent)"
                : "transparent",
              color: isActive
                ? "var(--sidebar-foreground)"
                : "rgba(232,245,224,0.7)",
            })}
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div
        className="px-5 py-4 border-t text-xs"
        style={{
          borderColor: "var(--sidebar-border)",
          color: "rgba(232,245,224,0.4)",
        }}
      >
        Dados até {formatarData(dados.base.fim)}
        <br />
        Jardim Canadá · Itabirito
      </div>
    </aside>
  );
}