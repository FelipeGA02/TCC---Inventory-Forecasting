import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { Flower2, Loader2, LogIn } from "lucide-react";
import { ApiError, mensagemDoErro } from "@/lib/http/errors";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "./AuthContext";

function mensagemDeLogin(erro: unknown): string {
  // No login, 401 é senha errada (a mensagem padrão do 401 fala de sessão expirada).
  if (erro instanceof ApiError && erro.status === 401) return erro.detail ?? "E-mail ou senha incorretos.";
  return mensagemDoErro(erro);
}

export function LoginPage() {
  const { usuario, entrar } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = (location.state as { de?: string } | null)?.de ?? "/";
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (usuario) return <Navigate to={destino} replace />;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(email, senha);
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(mensagemDeLogin(falha));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: "var(--background)" }}>
      <div className="w-full max-w-sm flex flex-col gap-6">
        <div className="flex items-center gap-3 justify-center">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: "var(--primary)" }}>
            <Flower2 size={22} color="#fff" />
          </div>
          <div>
            <p className="text-base leading-tight" style={{ color: "var(--foreground)", fontWeight: 700 }}>
              Verde Perto
            </p>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              Sistema de Previsão de Vendas
            </p>
          </div>
        </div>

        <Card className="border" style={{ borderColor: "var(--border)" }}>
          <CardContent className="p-6">
            <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
              <div>
                <p className="text-base" style={{ color: "var(--foreground)", fontWeight: 600 }}>
                  Entrar
                </p>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  Use o e-mail e a senha cadastrados para a sua loja.
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  autoFocus
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="gestora@floricultura.com"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="senha">Senha</Label>
                <Input
                  id="senha"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                />
              </div>
              {erro && (
                <p
                  role="alert"
                  className="text-sm rounded-md px-3 py-2"
                  style={{ background: "rgba(212,24,61,0.08)", color: "var(--destructive)" }}
                >
                  {erro}
                </p>
              )}
              <Button
                type="submit"
                disabled={enviando || !email || !senha}
                className="gap-2"
                style={{ background: "var(--primary)", color: "#fff" }}
              >
                {enviando ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
                {enviando ? "Entrando..." : "Entrar"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
