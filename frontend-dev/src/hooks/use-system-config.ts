import { useQuery } from "@tanstack/react-query";

import api from "@/lib/api";

export type SystemConfig = {
  features: {
    email_enabled: boolean;
    ai_controls_enabled: boolean;
  };
  registration: {
    mode: "open" | "allowlist" | "invite_only";
    invite_required: boolean;
  };
};

export function useSystemConfig() {
  return useQuery({
    queryKey: ["system-config"],
    queryFn: async (): Promise<SystemConfig> => {
      const response = await api.get("/v1/system/config");
      return response.data;
    },
    staleTime: 30_000,
  });
}
