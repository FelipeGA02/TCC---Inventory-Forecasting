/**
 * Andamento do serviço de previsão (`/api/v1/servico-previsao/*`), **só para admin**: o
 * botão "Treinar previsões" e a aba de notificações leem o mesmo estado.
 *
 * Consulta o status a cada 3 s enquanto há treino em andamento e a cada minuto fora disso.
 * Quando um treino que estava em andamento termina, avisa por toast. Para quem não é
 * admin nada é consultado (a API responderia 403).
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { useAuth } from "../auth/AuthContext";
import { api, type DisparoTreino, type StatusServicoPrevisao } from "./api";

const DURANTE_TREINO_MS = 3_000;
const FORA_DO_TREINO_MS = 60_000;

interface ServicoPrevisaoValor {
  /** usuário admin: só ele vê e usa o serviço */
  disponivel: boolean;
  status: StatusServicoPrevisao | null;
  atualizar: () => Promise<StatusServicoPrevisao | null>;
  disparar: () => Promise<DisparoTreino>;
}

const ServicoPrevisaoContext = createContext<ServicoPrevisaoValor | null>(null);

export function ServicoPrevisaoProvider({ children }: { children: ReactNode }) {
  const { usuario } = useAuth();
  const admin = usuario?.perfil === "admin";
  const [status, setStatus] = useState<StatusServicoPrevisao | null>(null);
  // id do treino que estava em andamento na consulta anterior, para avisar quando terminar
  const andamentoAnterior = useRef<number | null>(null);

  const atualizar = useCallback(async () => {
    if (!admin) return null;
    try {
      const s = await api.statusServicoPrevisao();
      const anterior = andamentoAnterior.current;
      if (anterior !== null && !s.em_andamento && s.ultimo?.id === anterior) {
        if (s.ultimo.status === "done") toast.success(s.ultimo.mensagem ?? "Previsões treinadas.");
        else if (s.ultimo.status === "error") toast.error(s.ultimo.mensagem ?? "O treino das previsões falhou.");
      }
      andamentoAnterior.current = s.em_andamento?.id ?? null;
      setStatus(s);
      return s;
    } catch {
      return null; // consulta de fundo: tenta de novo no próximo ciclo
    }
  }, [admin]);

  const emAndamento = Boolean(status?.em_andamento);
  useEffect(() => {
    if (!admin) {
      setStatus(null);
      return;
    }
    void atualizar();
    const id = window.setInterval(() => void atualizar(), emAndamento ? DURANTE_TREINO_MS : FORA_DO_TREINO_MS);
    return () => window.clearInterval(id);
  }, [admin, emAndamento, atualizar]);

  const disparar = useCallback(async () => {
    const resposta = await api.treinarPrevisoes();
    if (resposta.iniciado) andamentoAnterior.current = resposta.treino.id;
    await atualizar();
    return resposta;
  }, [atualizar]);

  return (
    <ServicoPrevisaoContext.Provider value={{ disponivel: admin, status, atualizar, disparar }}>
      {children}
    </ServicoPrevisaoContext.Provider>
  );
}

export function useServicoPrevisao(): ServicoPrevisaoValor {
  const ctx = useContext(ServicoPrevisaoContext);
  if (!ctx) throw new Error("useServicoPrevisao precisa estar dentro de <ServicoPrevisaoProvider>");
  return ctx;
}
