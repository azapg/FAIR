import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";
import { Providers } from "./providers";
import { App } from "./index";

import ErrorBoundary from "./components/ErrorBoundary";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Toaster } from "sonner";
import "@/i18n";

function MainLayout() {
  const location = useLocation();
  const isAuthPage = ["/login", "/register"].includes(location.pathname);

  if (isAuthPage) {
    return (
      <div className="min-h-svh w-full">
        <Toaster richColors position="bottom-left" />
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </div>
    );
  }

  return (
    <SidebarProvider
      className="flex min-h-svh w-full flex-col"
      cookieName="app_sidebar_state"
      keyboardShortcut="g"
    >
        <div className="h-full flex">
          <AppSidebar />
          <SidebarInset>
            <Toaster richColors position="bottom-left" />
            <ErrorBoundary>
              <App />
            </ErrorBoundary>
          </SidebarInset>
        </div>
    </SidebarProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Providers>
      <BrowserRouter>
        <MainLayout />
      </BrowserRouter>
    </Providers>
  </React.StrictMode>,
);
