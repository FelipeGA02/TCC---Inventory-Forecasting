import { env } from "@/config/env";

export function responderMock<T>(dados: T, signal?: AbortSignal): Promise<T> {
  return new Promise<T>((resolver, rejeitar) => {
    if (signal?.aborted) {
      rejeitar(new DOMException("Aborted", "AbortError"));
      return;
    }

    const temporizador = setTimeout(() => resolver(dados), env.mockLatencyMs);

    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(temporizador);
        rejeitar(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}
