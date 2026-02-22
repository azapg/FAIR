import type { ReactNode } from "react";

type SettingsSectionCardProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export function SettingsSectionCard({
  title,
  description,
  children,
}: SettingsSectionCardProps) {
  return (
    <section className="rounded-lg bg-card p-5">
      <header className="mb-4 space-y-1">
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </header>
      <div className="space-y-4">{children}</div>
    </section>
  );
}
