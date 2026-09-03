import { Navigate, useLocation } from "react-router";
import type { ReactNode } from "react";
import type { Perfil } from "@/domain/types";
import { useAuth } from "./AuthContext";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";

export function PrivateRoute({ children, perfil }: { children: ReactNode; perfil?: Perfil }) {
  const { autenticado, inicializando, temPerfil } = useAuth();
  const location = useLocation();

  if (inicializando) return <TelaCarregando mensagem="Abrindo sua sessão…" />;

  if (!autenticado) return <Navigate to="/login" replace state={{ de: location.pathname }} />;

  if (perfil && !temPerfil(perfil)) return <Navigate to="/" replace />;

  return <>{children}</>;
}
