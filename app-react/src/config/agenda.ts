/**
 * Agenda das rotinas automáticas do backend (APScheduler), espelhando o `.env` do CLAUDE.md:
 *   RETRAIN_DAY_OF_WEEK=mon · RETRAIN_HOUR=2 · DAILY_FORECAST_HOUR=3
 * Quando a API estiver conectada, estes valores virão de `/api/v1/models/status`.
 */
export const AGENDA = {
  /** Dia da semana do ajuste (treino) dos modelos: 0 = domingo … 1 = segunda. */
  treinoDiaSemana: 1,
  treinoHora: 2,
  /** Hora da geração diária da previsão a partir dos modelos já treinados. */
  previsaoHora: 3,
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

/** Próxima ocorrência de uma hora do dia (hoje ou amanhã). */
export function proximaHora(agora: Date, hora: number): Date {
  const d = new Date(agora);
  d.setHours(hora, 0, 0, 0);
  if (d <= agora) d.setDate(d.getDate() + 1);
  return d;
}
