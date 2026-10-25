/**
 * Telas do sistema (depois do login). O layout (menu lateral e cabeçalho) aparece na hora;
 * a área da tela espera o contexto (`CarregarDados`) e, em cada rota, `<Tela>` busca os
 * dados daquela tela antes de carregar o módulo dela (`lazy`): as telas leem os dados no
 * nível do módulo (filtros, nomes de categoria), então só são importadas depois deles.
 */
import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router";
import { Sidebar } from "./components/layout/Sidebar";
import { Header } from "./components/layout/Header";
import { CarregandoTela, ErroTela, Tela } from "./components/layout/Tela";
import { FiltroLojaProvider } from "./components/shared";
import { useDados } from "./data/CarregarDados";
import { ServicoPrevisaoProvider } from "./data/ServicoPrevisao";

const Dashboard = lazy(() => import("./components/screens/Dashboard").then((m) => ({ default: m.Dashboard })));
const ImportarPlanilha = lazy(() => import("./components/screens/ImportarPlanilha").then((m) => ({ default: m.ImportarPlanilha })));
const PreVisualizacao = lazy(() => import("./components/screens/PreVisualizacao").then((m) => ({ default: m.PreVisualizacao })));
const PrevisaoSarimax = lazy(() => import("./components/screens/PrevisaoSarimax").then((m) => ({ default: m.PrevisaoSarimax })));
const ExportarRelatorios = lazy(() => import("./components/screens/ExportarRelatorios").then((m) => ({ default: m.ExportarRelatorios })));

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--background)" }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

function Rotas() {
  const { contexto, erro, versao, tentarDeNovo } = useDados();
  if (!contexto) {
    return erro ? <ErroTela mensagem={erro} onTentar={tentarDeNovo} /> : <CarregandoTela mensagem="Carregando as lojas e as categorias..." />;
  }
  return (
    <Routes key={versao}>
      <Route path="/" element={<Tela key="inicio" recursos={["analises"]} mensagem="Carregando as vendas..."><Dashboard /></Tela>} />
      <Route path="/importar" element={<Tela key="importar" mensagem="Abrindo..."><ImportarPlanilha /></Tela>} />
      <Route path="/pre-visualizacao" element={<Tela key="registros" mensagem="Abrindo..."><PreVisualizacao /></Tela>} />
      <Route path="/previsao" element={<Tela key="previsao" recursos={["painel"]} mensagem="Carregando a previsão..."><PrevisaoSarimax /></Tela>} />
      <Route path="/exportar" element={<Tela key="exportar" recursos={["painel"]} mensagem="Carregando os dados dos relatórios..."><ExportarRelatorios /></Tela>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function AppAutenticado() {
  return (
    <FiltroLojaProvider>
      <ServicoPrevisaoProvider>
        <Layout>
          <Rotas />
        </Layout>
      </ServicoPrevisaoProvider>
    </FiltroLojaProvider>
  );
}
