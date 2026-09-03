import { NavLink } from "react-router";
import { Flower2 } from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { rotasPara } from "@/app/routes";

export function Sidebar() {
  const { usuario } = useAuth();
  const itens = rotasPara(usuario?.perfil);

  return (
    <aside className="w-60 shrink-0 flex flex-col" style={{ background: "var(--sidebar)" }}>
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
          <p className="text-sm leading-tight" style={{ color: "var(--sidebar-foreground)", fontWeight: 600 }}>
            Verde Perto
          </p>
          <p className="text-xs" style={{ color: "rgba(232,245,224,0.55)" }}>
            Sistema de Previsão
          </p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 flex flex-col gap-1" aria-label="Navegação principal">
        {itens.map(({ path, icone: Icone, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? "font-medium" : "hover:opacity-80"
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? "var(--sidebar-accent)" : "transparent",
              color: isActive ? "var(--sidebar-foreground)" : "rgba(232,245,224,0.7)",
            })}
          >
            <Icone size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div
        className="px-5 py-4 border-t text-xs"
        style={{ borderColor: "var(--sidebar-border)", color: "rgba(232,245,224,0.4)" }}
      >
        v2.4.1 · Floricultura SA
      </div>
    </aside>
  );
}
