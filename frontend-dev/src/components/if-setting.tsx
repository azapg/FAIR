import { ReactNode } from "react";

import { useLocalPreference } from "@/hooks/use-local-preference";
import { useUserSetting } from "@/hooks/use-user-settings";

type IfSettingScope = "local" | "user" | "local-first";

type IfSettingProps = {
  setting: string;
  equals?: unknown;
  scope?: IfSettingScope;
  fallback?: ReactNode;
  children: ReactNode;
};

export function IfSetting({
  setting,
  equals,
  scope = "local-first",
  fallback = null,
  children,
}: IfSettingProps) {
  const localSetting = useLocalPreference(setting).value;
  const userSetting = useUserSetting(setting).value;

  const candidate =
    scope === "local"
      ? localSetting
      : scope === "user"
        ? userSetting
        : localSetting !== undefined
          ? localSetting
          : userSetting;

  const allowed =
    equals === undefined ? Boolean(candidate) : Object.is(candidate, equals);

  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
