/**
 * Agenda das rotinas automáticas do backend (APScheduler), espelhando o `.env` do CLAUDE.md:
 *   RETRAIN_DAY_OF_WEEK=mon · RETRAIN_HOUR=2
 * O treino é pulado quando não há venda nova, e a previsão é gerada logo depois de cada
 * treino (60 dias; a tela mostra os 14 a partir de hoje). A conferência das 03:00
 * (DAILY_FORECAST_HOUR) só gera de novo se o calendário mudou, por isso não aparece aqui.
 * Quando a API estiver conectada, estes valores virão de `/api/v1/models/status`.
 */
export const AGENDA = {
  /** Dia da semana do ajuste (treino) dos modelos: 0 = domingo … 1 = segunda. */
  treinoDiaSemana: 1,
  treinoHora: 2,
  /** A partir de quantos dias sem vendas novas a base é considerada desatualizada. */
  diasParaDesatualizado: 7,
} as const;

/** Próxima ocorrência de um dia da semana + hora, a partir de `agora`. */
export function proximoDiaSemana(agora: Date, diaSemana: number, hora: number): Date {
  const d = new Date(agora);
  d.setHours(hora, 0, 0, 0);
  const faltam = (diaSemana - d.getDay() + 7) % 7;
  d.setDate(d.getDate() + faltam);
  if (d <= agora) d.setDate(d.getDate() + 7);
  return d;
}
