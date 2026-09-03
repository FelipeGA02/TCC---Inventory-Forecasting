import { Navigate, Route, Routes } from "react-router";
import { AppProviders } from "./providers/AppProviders";
import { AppLayout } from "./layout/AppLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { PrivateRoute } from "@/features/auth/PrivateRoute";
import { rotas } from "./routes";

export default function App() {
  return (
    <AppProviders>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <PrivateRoute>
              <AppLayout />
            </PrivateRoute>
          }
        >
          {rotas.map(({ path, perfil, componente: Tela }) => (
            <Route
              key={path}
              path={path}
              element={
                perfil === "admin" ? (
                  <PrivateRoute perfil="admin">
                    <Tela />
                  </PrivateRoute>
                ) : (
                  <Tela />
                )
              }
            />
          ))}
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppProviders>
  );
}
