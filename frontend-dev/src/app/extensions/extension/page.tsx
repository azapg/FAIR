import { useEffect, useMemo, useState } from "react";
import { Copy } from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { usePermission } from "@/hooks/use-permission";
import { useExtension, useRotateExtensionSecret, useUpdateExtension } from "@/hooks/use-extensions";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type ExtensionLocationState = {
  extensionSecret?: string;
};

const parseScopesInput = (value: string): string[] =>
  Array.from(
    new Set(
      value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ).sort((a, b) => a.localeCompare(b));

export default function ExtensionDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ id: string }>();
  const extensionId = params.id ?? "";

  const canManageExtensions = usePermission("admin");
  const { data: extension, isLoading, isError } = useExtension(extensionId, canManageExtensions);
  const updateExtension = useUpdateExtension();
  const rotateSecret = useRotateExtensionSecret();

  const [enabled, setEnabled] = useState(true);
  const [scopesText, setScopesText] = useState("");
  const [confirmRotateOpen, setConfirmRotateOpen] = useState(false);
  const [secretDialogOpen, setSecretDialogOpen] = useState(false);
  const [lastSecret, setLastSecret] = useState("");

  useEffect(() => {
    if (!extension) return;
    setEnabled(extension.enabled);
    setScopesText((extension.scopes ?? []).join(", "));
  }, [extension]);

  useEffect(() => {
    const state = (location.state ?? null) as ExtensionLocationState | null;
    if (!state?.extensionSecret) return;
    setLastSecret(state.extensionSecret);
    setSecretDialogOpen(true);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const normalizedScopes = useMemo(() => parseScopesInput(scopesText), [scopesText]);
  const originalScopes = useMemo(
    () => [...(extension?.scopes ?? [])].sort((a, b) => a.localeCompare(b)),
    [extension?.scopes],
  );
  const scopesChanged = normalizedScopes.join(",") !== originalScopes.join(",");
  const enabledChanged = enabled !== !!extension?.enabled;
  const canSave = !!extension && (scopesChanged || enabledChanged) && !updateExtension.isPending;

  const handleSave = async () => {
    if (!extension) return;
    await updateExtension.mutateAsync({
      extensionId: extension.extensionId,
      enabled,
      scopes: normalizedScopes,
    });
  };

  const handleRotateSecret = async () => {
    if (!extension) return;
    const rotated = await rotateSecret.mutateAsync(extension.extensionId);
    setConfirmRotateOpen(false);
    setLastSecret(rotated.extensionSecret);
    setSecretDialogOpen(true);
  };

  const handleCopySecret = async () => {
    try {
      await navigator.clipboard.writeText(lastSecret);
      toast.success(t("extensions.secretCopied"));
    } catch {
      toast.error(t("extensions.secretCopyFailed"));
    }
  };

  return (
    <main className="flex flex-col justify-center">
      <div className="px-5 py-2">
        <BreadcrumbNav
          segments={[
            { label: t("extensions.title"), slug: "extensions" },
            { label: extensionId, slug: extensionId },
          ]}
        />
      </div>

      <div className="px-6 pt-3">
        <h1 className="text-3xl font-semibold tracking-tight">{extensionId}</h1>
        <p className="text-sm text-muted-foreground">{t("extensions.detailSubtitle")}</p>
      </div>

      <div className="px-6 py-4">
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
              <CardDescription>{t("extensions.notFound")}</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button variant="outline" onClick={() => navigate("/extensions")}>
                {t("extensions.backToList")}
              </Button>
            </CardFooter>
          </Card>
        )}

        {canManageExtensions && extension && !isLoading && !isError && (
          <Card>
            <CardHeader>
              <CardTitle>{t("extensions.permissionsTitle")}</CardTitle>
              <CardDescription>{t("extensions.permissionsDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <Label htmlFor="extension-enabled">{t("extensions.enabledLabel")}</Label>
                  <p className="text-sm text-muted-foreground">{t("extensions.enabledHelp")}</p>
                </div>
                <Switch id="extension-enabled" checked={enabled} onCheckedChange={setEnabled} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="extension-scopes">{t("extensions.scopesLabel")}</Label>
                <Input
                  id="extension-scopes"
                  value={scopesText}
                  onChange={(event) => setScopesText(event.target.value)}
                  placeholder={t("extensions.scopesPlaceholder")}
                />
                <p className="text-sm text-muted-foreground">{t("extensions.scopesHelp")}</p>
              </div>
            </CardContent>
            <CardFooter className="gap-2">
              <Button onClick={handleSave} disabled={!canSave}>
                {updateExtension.isPending ? t("common.wait") : t("common.save")}
              </Button>
              <Button
                variant="outline"
                onClick={() => setConfirmRotateOpen(true)}
                disabled={rotateSecret.isPending}
              >
                {t("extensions.resetSecret")}
              </Button>
            </CardFooter>
          </Card>
        )}
      </div>

      <AlertDialog open={confirmRotateOpen} onOpenChange={setConfirmRotateOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("extensions.resetSecretConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("extensions.resetSecretConfirmDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleRotateSecret}>
              {rotateSecret.isPending ? t("common.wait") : t("extensions.resetSecret")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={secretDialogOpen} onOpenChange={setSecretDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("extensions.secretDialogTitle")}</DialogTitle>
            <DialogDescription>{t("extensions.secretDialogDescription")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="extension-secret">{t("extensions.secretLabel")}</Label>
            <Input id="extension-secret" value={lastSecret} readOnly />
            <p className="text-sm text-muted-foreground">{t("extensions.secretOneTime")}</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCopySecret}>
              <Copy className="mr-2 h-4 w-4" />
              {t("extensions.copySecret")}
            </Button>
            <Button type="button" onClick={() => setSecretDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
