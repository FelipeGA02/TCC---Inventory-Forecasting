import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { Loader2 } from "lucide-react";
import type { Perfil } from "@/domain/types";
import { useAuth } from "./AuthContext";

/** Tela de espera em tela cheia (sessão sendo retomada, dados carregando). */
export function TelaCarregando({ mensagem }: { mensagem: string }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-3" style={{ background: "var(--background)" }}>
      <Loader2 size={32} className="animate-spin" style={{ color: "var(--primary)" }} />
      <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
        {mensagem}
      </p>
    </div>
  );
}

/**
 * Só mostra `children` com sessão ativa; sem sessão, manda para o login e volta para a
 * mesma página depois. Com `perfil`, exige também o perfil (ex.: "admin").
 */
export function PrivateRoute({ children, perfil }: { children: ReactNode; perfil?: Perfil }) {
  const { usuario, carregando } = useAuth();
  const location = useLocation();

  if (carregando) return <TelaCarregando mensagem="Retomando sua sessão..." />;
  if (!usuario) return <Navigate to="/login" replace state={{ de: location.pathname + location.search }} />;
  if (perfil && usuario.perfil !== perfil) return <Navigate to="/" replace />;
  return <>{children}</>;
}
