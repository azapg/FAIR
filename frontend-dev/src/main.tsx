import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Providers } from "./providers";
import { App } from "./index";
import Header from "@/components/header";
import ErrorBoundary from "./components/ErrorBoundary";
import { Toaster } from "sonner";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Providers>
      <BrowserRouter>
        <ErrorBoundary>
          <Header />
        </ErrorBoundary>
        <div className={"pt-16 h-full"}>
          <Toaster richColors position="top-right" />
          <ErrorBoundary>
            <App />
          </ErrorBoundary>
        </div>
      </BrowserRouter>
    </Providers>
  </React.StrictMode>
);
