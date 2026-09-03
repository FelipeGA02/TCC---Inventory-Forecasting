import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { Flower2, Loader2 } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { cores, estiloUrgencia } from "@/styles/tokens";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { entrar, entrando, erro, autenticado, inicializando } = useAuth();
  const navegar = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

  const destino = (location.state as { de?: string } | null)?.de ?? "/";

  if (!inicializando && autenticado) return <Navigate to={destino} replace />;

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    if (await entrar(email, senha)) navegar(destino, { replace: true });
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: cores.fundo }}>
      <Card className="w-full max-w-sm border" style={{ borderColor: cores.borda }}>
        <CardContent className="p-7 flex flex-col gap-6">
          <div className="flex flex-col items-center gap-3 text-center">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: cores.primaria }}
            >
              <Flower2 size={24} color="#fff" />
            </div>
            <div>
              <p className="text-base" style={{ color: cores.texto, fontWeight: 600 }}>
                Verde Perto
              </p>
              <p className="text-xs" style={{ color: cores.textoSuave }}>
                Sistema de Previsão de Estoque
              </p>
            </div>
          </div>

          <form className="flex flex-col gap-4" onSubmit={aoEnviar}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="text-xs">
                E-mail
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(evento) => setEmail(evento.target.value)}
                placeholder="voce@floricultura.com"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="senha" className="text-xs">
                Senha
              </Label>
              <Input
                id="senha"
                type="password"
                autoComplete="current-password"
                required
                value={senha}
                onChange={(evento) => setSenha(evento.target.value)}
              />
            </div>

            {erro && (
              <p
                className="text-xs rounded-lg px-3 py-2"
                role="alert"
                style={{
                  background: estiloUrgencia.critico.fundo,
                  color: estiloUrgencia.critico.cor,
                  border: `1px solid ${estiloUrgencia.critico.borda}`,
                }}
              >
                {erro}
              </p>
            )}

            <Button type="submit" className="w-full gap-2" disabled={entrando}>
              {entrando && <Loader2 size={15} className="animate-spin" />}
              {entrando ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
