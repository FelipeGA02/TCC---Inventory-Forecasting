import { useLocation } from "react-router";
import { Bell, LogOut, RefreshCw, User } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { useAuth } from "@/features/auth/AuthContext";
import { rotaPor } from "@/app/routes";
import { cores } from "@/styles/tokens";

export function Header() {
  const { pathname } = useLocation();
  const { usuario, sair } = useAuth();
  const rota = rotaPor(pathname);

  return (
    <header
      className="h-16 shrink-0 flex items-center justify-between px-6 border-b bg-white"
      style={{ borderColor: cores.borda }}
    >
      <div>
        <h1 className="text-base" style={{ color: cores.texto, fontWeight: 600, lineHeight: 1.3 }}>
          {rota?.titulo ?? "Verde Perto"}
        </h1>
        <p className="text-xs" style={{ color: cores.textoSuave, lineHeight: 1.3 }}>
          {rota?.subtitulo ?? ""}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="gap-2 text-xs" style={{ color: cores.textoSuave }}>
          <RefreshCw size={14} />
          Atualizar
        </Button>

        <button
          type="button"
          aria-label="Notificações"
          className="relative w-9 h-9 rounded-lg flex items-center justify-center hover:opacity-80 transition-colors"
          style={{ background: "var(--muted)" }}
        >
          <Bell size={16} style={{ color: cores.textoSuave }} />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ background: cores.destaque }}
          />
        </button>

        <div className="flex items-center gap-2 pl-1">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{ background: cores.primaria }}
            title={usuario?.email ?? ""}
          >
            <User size={16} color="#fff" />
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="gap-2 text-xs"
            style={{ color: cores.textoSuave }}
            onClick={sair}
          >
            <LogOut size={14} />
            Sair
          </Button>
        </div>
      </div>
    </header>
  );
}
