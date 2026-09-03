import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import {
  Bell,
  FileDown,
  FlaskConical,
  LayoutDashboard,
  Table2,
  TrendingUp,
  Upload,
  type LucideIcon,
} from "lucide-react";
import type { Perfil } from "@/domain/types";

export interface RotaApp {
  path: string;
  label: string;
  titulo: string;
  subtitulo: string;
  icone: LucideIcon;
  perfil: Perfil;
  componente: LazyExoticComponent<ComponentType>;
}

const carregar = <T extends { [K in N]: ComponentType }, N extends string>(
  importar: () => Promise<T>,
  nome: N,
) => lazy(() => importar().then((modulo) => ({ default: modulo[nome] })));

export const rotas: RotaApp[] = [
  {
    path: "/",
    label: "Início",
    titulo: "Início",
    subtitulo: "Resumo geral das vendas e alertas de hoje",
    icone: LayoutDashboard,
    perfil: "viewer",
    componente: carregar(() => import("@/features/dashboard/DashboardPage"), "DashboardPage"),
  },
  {
    path: "/importar",
    label: "Carregar Planilha",
    titulo: "Carregar Planilha de Vendas",
    subtitulo: "Envie os dados de vendas para atualizar as previsões",
    icone: Upload,
    perfil: "admin",
    componente: carregar(() => import("@/features/upload/UploadPage"), "UploadPage"),
  },
  {
    path: "/pre-visualizacao",
    label: "Conferir Dados",
    titulo: "Conferir Dados Enviados",
    subtitulo: "Verifique se os dados estão corretos antes de calcular",
    icone: Table2,
    perfil: "viewer",
    componente: carregar(() => import("@/features/preview/PreviewPage"), "PreviewPage"),
  },
  {
    path: "/previsao",
    label: "Previsão de Compras",
    titulo: "Previsão de Compras",
    subtitulo: "Veja quanto comprar de cada produto nas próximas semanas",
    icone: TrendingUp,
    perfil: "viewer",
    componente: carregar(() => import("@/features/forecast/ForecastPage"), "ForecastPage"),
  },
  {
    path: "/alertas",
    label: "Produtos para Repor",
    titulo: "Produtos para Repor",
    subtitulo: "Itens com estoque baixo que precisam de atenção",
    icone: Bell,
    perfil: "viewer",
    componente: carregar(() => import("@/features/alerts/AlertsPage"), "AlertsPage"),
  },
  {
    path: "/simulador",
    label: "Simular Promoções",
    titulo: "Simular Promoções",
    subtitulo: "Veja o impacto estimado de descontos e ofertas especiais",
    icone: FlaskConical,
    perfil: "viewer",
    componente: carregar(() => import("@/features/simulation/SimulationPage"), "SimulationPage"),
  },
  {
    path: "/exportar",
    label: "Baixar Relatórios",
    titulo: "Baixar Relatórios",
    subtitulo: "Gere e salve relatórios em PDF ou Excel",
    icone: FileDown,
    perfil: "viewer",
    componente: carregar(() => import("@/features/reports/ReportsPage"), "ReportsPage"),
  },
];

export function rotaPor(pathname: string): RotaApp | undefined {
  return rotas.find((rota) => rota.path === pathname);
}

export function rotasPara(perfil: Perfil | undefined): RotaApp[] {
  if (perfil === "admin") return rotas;
  return rotas.filter((rota) => rota.perfil === "viewer");
}
