import { BrowserRouter, Navigate, Routes, Route } from "react-router";
import { Toaster } from "sonner";
import { Sidebar } from "./components/layout/Sidebar";
import { Header } from "./components/layout/Header";
import { Dashboard } from "./components/screens/Dashboard";
import { ImportarPlanilha } from "./components/screens/ImportarPlanilha";
import { PreVisualizacao } from "./components/screens/PreVisualizacao";
import { PrevisaoSarimax } from "./components/screens/PrevisaoSarimax";
import { FiltroLojaProvider } from "./components/shared";
import { ExportarRelatorios } from "./components/screens/ExportarRelatorios";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--background)" }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <FiltroLojaProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/importar" element={<ImportarPlanilha />} />
            <Route path="/pre-visualizacao" element={<PreVisualizacao />} />
            <Route path="/previsao" element={<PrevisaoSarimax />} />
            <Route path="/exportar" element={<ExportarRelatorios />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </FiltroLojaProvider>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  );
}
