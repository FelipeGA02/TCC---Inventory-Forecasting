/** Endereços, caminhos e credenciais dos testes de ponta a ponta (compartilhados pela config e pelos testes). */
import path from "node:path";

export const API_PORTA = 8100;
export const FRONT_PORTA = 5174;
export const API_URL = `http://127.0.0.1:${API_PORTA}`;
export const FRONT_URL = `http://localhost:${FRONT_PORTA}`;

export const APP_REACT = path.resolve(import.meta.dirname, "..");
export const IA_PREDICTOR = path.resolve(APP_REACT, "../ia-predictor");
/** Python do ambiente virtual da API; `E2E_PYTHON` troca (ex.: CI com outro caminho). */
export const PYTHON =
  process.env.E2E_PYTHON ??
  path.join(IA_PREDICTOR, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");

/** Onde ficam as fotos de cada fluxo (versionáveis: servem de documentação das telas). */
export const PASTA_FOTOS = path.join(APP_REACT, "e2e", "fotos");
/** Arquivos gerados para os testes (planilha de importação) — fora do git. */
export const PASTA_SAIDA = path.join(APP_REACT, "e2e", ".saida");
export const PLANILHA_MARCO = path.join(PASTA_SAIDA, "vendas 02 a 07-03-2026.xlsx");
export const PLANILHA_COM_FALTA = path.join(PASTA_SAIDA, "vendas 11 a 13-03-2026.xlsx");
export const PLANILHA_TEXTO = path.join(PASTA_SAIDA, "vendas.csv");

/** Os mesmos de `ia-predictor/tests/e2e/servidor.py` (só valem no banco dos testes). */
export const USUARIOS = {
  admin: { email: "gestora@floricultura.com", senha: "senha-admin-e2e", nome: "Gestora (administração)" },
  viewer: { email: "gerente@floricultura.com", senha: "senha-viewer-e2e", nome: "Gerente (consulta)" },
} as const;
export type Perfil = keyof typeof USUARIOS;
