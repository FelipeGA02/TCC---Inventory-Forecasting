import { Component, type ErrorInfo, type ReactNode } from "react";
import { EstadoErro } from "@/app/components/feedback/EstadoErro";

interface Props {
  children: ReactNode;
}

interface State {
  falhou: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { falhou: false };

  static getDerivedStateFromError(): State {
    return { falhou: true };
  }

  componentDidCatch(erro: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", erro, info.componentStack);
  }

  private recarregar = (): void => {
    this.setState({ falhou: false });
  };

  render(): ReactNode {
    if (this.state.falhou) {
      return (
        <EstadoErro
          mensagem="Esta tela não conseguiu carregar. Tente de novo ou volte ao início."
          aoTentarNovamente={this.recarregar}
        />
      );
    }
    return this.props.children;
  }
}
