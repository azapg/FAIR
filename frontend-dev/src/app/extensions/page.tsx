import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePermission } from "@/hooks/use-permission";
import { useCreateExtension, useExtensions } from "@/hooks/use-extensions";

export default function ExtensionsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const canManageExtensions = usePermission("admin");
  const { data: extensions = [], isLoading, isError } = useExtensions(canManageExtensions);
  const createExtension = useCreateExtension();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [extensionId, setExtensionId] = useState("");

  const trimmedExtensionId = extensionId.trim();
  const hasSpaces = /\s/.test(extensionId);
  const canSubmit = trimmedExtensionId.length > 0 && !hasSpaces && !createExtension.isPending;

  const sortedExtensions = useMemo(
    () => [...extensions].sort((a, b) => a.extensionId.localeCompare(b.extensionId)),
    [extensions],
  );

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    const created = await createExtension.mutateAsync({
      extensionId: trimmedExtensionId,
      scopes: [],
      enabled: true,
    });
    setDialogOpen(false);
    setExtensionId("");
    navigate(`/extensions/${created.extensionId}`, {
      state: { extensionSecret: created.extensionSecret },
    });
  };

  return (
    <main className="flex flex-col justify-center">
      <div className="px-5 py-2">
        <BreadcrumbNav segments={[{ label: t("extensions.title"), slug: "extensions" }]} />
      </div>

      <div className="flex items-center justify-between px-6 pt-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t("extensions.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("extensions.subtitle")}</p>
        </div>
        {canManageExtensions && (
          <Button
            onClick={() => {
              setExtensionId("");
              setDialogOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("extensions.create")}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 px-6 py-4 md:grid-cols-2 xl:grid-cols-3">
        {!canManageExtensions && (
          <Card>
            <CardHeader>
              <CardTitle>{t("extensions.noAccessTitle")}</CardTitle>
              <CardDescription>{t("extensions.noAccessDescription")}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {canManageExtensions && isLoading && (
          <Card>
            <CardHeader>
              <CardTitle>{t("common.loading")}</CardTitle>
            </CardHeader>
          </Card>
        )}

        {canManageExtensions && isError && (
          <Card>
            <CardHeader>
              <CardTitle>{t("common.error")}</CardTitle>
              <CardDescription>{t("extensions.loadError")}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {canManageExtensions &&
          !isLoading &&
          !isError &&
          sortedExtensions.map((extension) => (
            <Card
              key={extension.extensionId}
              className="cursor-pointer transition-colors hover:bg-muted/40"
              onClick={() => navigate(`/extensions/${extension.extensionId}`)}
            >
              <CardHeader>
                <CardTitle className="break-all">{extension.extensionId}</CardTitle>
                <CardDescription>
                  {extension.enabled ? t("extensions.enabled") : t("extensions.disabled")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {t("extensions.scopeCount", { count: extension.scopes.length })}
                </p>
              </CardContent>
            </Card>
          ))}

        {canManageExtensions && !isLoading && !isError && sortedExtensions.length === 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t("extensions.emptyTitle")}</CardTitle>
              <CardDescription>{t("extensions.emptyDescription")}</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("extensions.createDialogTitle")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={onCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="extension-id">{t("extensions.idLabel")}</Label>
              <Input
                id="extension-id"
                autoFocus
                value={extensionId}
                onChange={(event) => setExtensionId(event.target.value)}
                placeholder={t("extensions.idPlaceholder")}
                disabled={createExtension.isPending}
              />
              {hasSpaces && (
                <p className="text-sm text-destructive">{t("extensions.idNoSpaces")}</p>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setDialogOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={!canSubmit}>
                {createExtension.isPending ? t("common.wait") : t("extensions.create")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
