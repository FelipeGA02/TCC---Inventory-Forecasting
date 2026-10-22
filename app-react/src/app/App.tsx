import { BrowserRouter, Routes, Route } from "react-router";
import { Toaster } from "sonner";
import { AuthProvider } from "./auth/AuthContext";
import { LoginPage } from "./auth/LoginPage";
import { PrivateRoute } from "./auth/PrivateRoute";
import { CarregarDados } from "./data/CarregarDados";
import AppAutenticado from "./AppAutenticado";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <CarregarDados>
                  <AppAutenticado />
                </CarregarDados>
              </PrivateRoute>
            }
          />
        </Routes>
      </AuthProvider>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  );
}
