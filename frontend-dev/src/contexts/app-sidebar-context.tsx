import React, { createContext, useContext, useMemo } from "react";
import { useSidebar } from "@/components/ui/sidebar";

type AppSidebarContextValue = {
  toggle: () => void;
  open: boolean;
  state: "expanded" | "collapsed";
  isMobile: boolean;
};

const AppSidebarContext = createContext<AppSidebarContextValue | null>(null);

export function useAppSidebar() {
  const ctx = useContext(AppSidebarContext);
  if (!ctx) {
    throw new Error("useAppSidebar must be used within AppSidebarContextBridge.");
  }
  return ctx;
}

export function AppSidebarContextBridge({
  children,
}: {
  children: React.ReactNode;
}) {
  const { toggleSidebar, open, state, isMobile } = useSidebar();

  const value = useMemo<AppSidebarContextValue>(
    () => ({
      toggle: toggleSidebar,
      open,
      state,
      isMobile,
    }),
    [toggleSidebar, open, state, isMobile],
  );

  return (
    <AppSidebarContext.Provider value={value}>
      {children}
    </AppSidebarContext.Provider>
  );
}