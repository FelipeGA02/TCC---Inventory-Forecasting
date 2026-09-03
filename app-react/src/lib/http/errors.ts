export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | undefined;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super("Não foi possível falar com o servidor. Verifique sua conexão e tente de novo.");
    this.name = "NetworkError";
    this.cause = cause;
  }
}

const MENSAGENS: Record<number, string> = {
  400: "Os dados enviados não foram aceitos. Confira as informações e tente de novo.",
  401: "Sua sessão expirou. Entre novamente para continuar.",
  403: "Você não tem permissão para fazer isso. Peça acesso à gestora.",
  404: "Não encontramos o que você procurou.",
  409: "Este envio já foi feito antes. Nada foi duplicado.",
  413: "O arquivo é grande demais. Envie uma planilha menor.",
  422: "A planilha tem colunas ou valores fora do formato esperado.",
  429: "Muitas tentativas seguidas. Espere um instante e tente de novo.",
  500: "O sistema teve um problema interno. Tente de novo em alguns minutos.",
  503: "O sistema está ocupado processando dados. Tente de novo em alguns minutos.",
};

export function mensagemPara(status: number): string {
  return MENSAGENS[status] ?? "Algo deu errado. Tente de novo em alguns minutos.";
}

export function mensagemDoErro(erro: unknown): string {
  if (erro instanceof ApiError || erro instanceof NetworkError) return erro.message;
  return "Algo deu errado. Tente de novo em alguns minutos.";
}
