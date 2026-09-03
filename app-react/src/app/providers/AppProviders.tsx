import type { ReactNode } from "react";
import { BrowserRouter } from "react-router";
import { Toaster } from "sonner";
import { AuthProvider } from "@/features/auth/AuthContext";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <AuthProvider>
        {children}
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
