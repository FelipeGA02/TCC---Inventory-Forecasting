import { Suspense } from "react";
import { Outlet } from "react-router";
import { ErrorBoundary } from "@/app/providers/ErrorBoundary";
import { TelaCarregando } from "@/app/components/feedback/TelaCarregando";
import { cores } from "@/styles/tokens";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: cores.fundo }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <ErrorBoundary>
            <Suspense fallback={<TelaCarregando />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
