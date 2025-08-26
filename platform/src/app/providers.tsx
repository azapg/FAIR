"use client";

import {QueryClientProvider} from "@tanstack/react-query";
import {queryClient} from "@/lib/queryClient";
import {AuthProvider} from "@/contexts/auth-context";
import {ThemeProvider} from "@/components/theme-provider";

export function Providers({children}: {children: React.ReactNode}) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

