import {QueryClientProvider} from "@tanstack/react-query";
import {queryClient} from "@/lib/queryClient";
import {AuthProvider} from "@/contexts/auth-context";
import {ThemeProvider} from "@/components/theme-provider"
import {ReactNode} from "react";


export function Providers({children}: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme={"system"}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}