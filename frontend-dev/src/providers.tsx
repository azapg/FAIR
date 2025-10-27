import {QueryClientProvider} from "@tanstack/react-query";
import {queryClient} from "@/lib/query-client";
import {AuthProvider} from "@/contexts/auth-context";
import {ThemeProvider} from "@/components/theme-provider"
import {ReactNode} from "react";
import {SessionSocketProvider} from "@/contexts/session-socket-context";


export function Providers({children}: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionSocketProvider>
        <ThemeProvider defaultTheme={"system"}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </SessionSocketProvider>
    </QueryClientProvider>
  );
}