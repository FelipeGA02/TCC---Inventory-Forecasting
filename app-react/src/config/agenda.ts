/**
 * Prazos dos avisos do sino de notificações. Não há treino agendado: a previsão é treinada
 * quando a gestora usa "Treinar previsões" depois de carregar as planilhas (ADR-017).
 */
export const AGENDA = {
  /** A partir de quantos dias sem vendas novas a base é considerada desatualizada. */
  diasParaDesatualizado: 7,
} as const;
