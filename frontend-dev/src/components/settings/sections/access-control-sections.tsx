import * as React from "react";
import { AxiosError } from "axios";
import { Copy, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import {
  type AIEntitlement,
  type CapabilityCostPolicy,
  useAdmissionRules,
  useAIEntitlements,
  useAIUsage,
  useCapabilityCostPolicies,
  useCreateAdmissionRule,
  useCreateRegistrationInvite,
  useDeleteAdmissionRule,
  usePlatformPolicy,
  useRegistrationInvites,
  useRevokeRegistrationInvite,
  useUpdateAIEntitlement,
  useUpdateCapabilityCostPolicy,
  useUpdatePlatformPolicy,
} from "@/hooks/use-access-controls";

function errorDescription(error: unknown) {
  const axiosError = error as AxiosError<{ detail?: string }>;
  return axiosError.response?.data?.detail ?? axiosError.message;
}

function reportFailure(error: unknown) {
  toast.error("Unable to update access controls", { description: errorDescription(error) });
}

export function AdmissionSection() {
  const { t } = useTranslation();
  const policy = usePlatformPolicy();
  const updatePolicy = useUpdatePlatformPolicy();
  const rules = useAdmissionRules();
  const createRule = useCreateAdmissionRule();
  const deleteRule = useDeleteAdmissionRule();
  const invites = useRegistrationInvites();
  const createInvite = useCreateRegistrationInvite();
  const revokeInvite = useRevokeRegistrationInvite();
  const [ruleKind, setRuleKind] = React.useState<"email" | "domain">("domain");
  const [ruleValue, setRuleValue] = React.useState("");
  const [inviteEmail, setInviteEmail] = React.useState("");
  const [inviteExpiryDays, setInviteExpiryDays] = React.useState("7");
  const [sendInviteEmail, setSendInviteEmail] = React.useState(false);
  const [lastInviteUrl, setLastInviteUrl] = React.useState<string | null>(null);

  const mode = policy.data?.effectiveAdmissionMode ?? "open";
  const closedWithoutRules = mode === "allowlist" && (rules.data?.length ?? 0) === 0;

  return (
    <div className="space-y-4">
      <SettingsSectionCard
        title={t("settings.access.admissionMode")}
        description={t("settings.access.admissionModeDescription")}
      >
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={mode}
            disabled={policy.isLoading || policy.data?.admissionLocked || updatePolicy.isPending}
            onValueChange={(value: "open" | "allowlist" | "invite_only") =>
              updatePolicy.mutate({ admissionMode: value }, { onError: reportFailure })
            }
          >
            <SelectTrigger className="w-56"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="open">{t("settings.access.open")}</SelectItem>
              <SelectItem value="allowlist">{t("settings.access.allowlist")}</SelectItem>
              <SelectItem value="invite_only">{t("settings.access.inviteOnly")}</SelectItem>
            </SelectContent>
          </Select>
          <Badge variant="outline">
            {policy.data?.admissionSource === "environment"
              ? t("settings.access.environmentLocked")
              : t("settings.access.databaseManaged")}
          </Badge>
        </div>
        {closedWithoutRules && (
          <p className="text-sm text-destructive">{t("settings.access.emptyAllowlistWarning")}</p>
        )}
      </SettingsSectionCard>

      <SettingsSectionCard
        title={t("settings.access.approvedEmails")}
        description={t("settings.access.approvedEmailsDescription")}
      >
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            createRule.mutate(
              { kind: ruleKind, value: ruleValue },
              {
                onSuccess: () => setRuleValue(""),
                onError: reportFailure,
              },
            );
          }}
        >
          <Select value={ruleKind} onValueChange={(value: "email" | "domain") => setRuleKind(value)}>
            <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="domain">{t("settings.access.domain")}</SelectItem>
              <SelectItem value="email">{t("settings.access.emailAddress")}</SelectItem>
            </SelectContent>
          </Select>
          <Input
            aria-label={t("settings.access.ruleValue")}
            value={ruleValue}
            onChange={(event) => setRuleValue(event.target.value)}
            placeholder={ruleKind === "domain" ? "example.edu" : "person@example.edu"}
            required
          />
          <Button type="submit" disabled={createRule.isPending}>{t("common.add")}</Button>
        </form>
        <div className="divide-y rounded-md border">
          {(rules.data ?? []).map((rule) => (
            <div key={rule.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <span><Badge variant="secondary" className="mr-2">{rule.kind}</Badge>{rule.value}</span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t("common.delete")}
                onClick={() => deleteRule.mutate(rule.id, { onError: reportFailure })}
              ><Trash2 className="size-4" /></Button>
            </div>
          ))}
          {!rules.isLoading && (rules.data?.length ?? 0) === 0 && (
            <p className="p-3 text-sm text-muted-foreground">{t("settings.access.noRules")}</p>
          )}
        </div>
      </SettingsSectionCard>

      <SettingsSectionCard
        title={t("settings.access.invitations")}
        description={t("settings.access.invitationsDescription")}
      >
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            createInvite.mutate(
              {
                email: inviteEmail,
                expiresInDays: Number(inviteExpiryDays),
                sendEmail: sendInviteEmail,
              },
              {
                onSuccess: (created) => {
                  setInviteEmail("");
                  setLastInviteUrl(created.registrationUrl);
                  if (sendInviteEmail) {
                    toast.success(t("settings.access.inviteEmailed"), {
                      description: inviteEmail,
                    });
                  }
                },
                onError: reportFailure,
              },
            );
          }}
        >
          <Input
            type="email"
            value={inviteEmail}
            onChange={(event) => setInviteEmail(event.target.value)}
            placeholder="person@example.edu"
            required
          />
          <Select
            value={inviteExpiryDays}
            onValueChange={setInviteExpiryDays}
          >
            <SelectTrigger className="sm:w-36" aria-label={t("settings.access.inviteExpiry")}><SelectValue /></SelectTrigger>
            <SelectContent>
              {[1, 3, 7, 14, 30, 90].map((days) => (
                <SelectItem key={days} value={String(days)}>
                  {t("settings.access.inviteExpiresIn", { count: days })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button type="submit" disabled={createInvite.isPending}>{t("settings.access.createInvite")}</Button>
          <label className="flex items-center gap-2 text-[13px] leading-4 text-muted-foreground sm:w-full">
            <input
              type="checkbox"
              className="size-4 accent-primary"
              checked={sendInviteEmail}
              onChange={(event) => setSendInviteEmail(event.target.checked)}
            />
            {t("settings.access.inviteAlsoSend")}
          </label>
        </form>
        {lastInviteUrl && (
          <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
            <p className="mb-2 text-[13px] leading-4 font-medium">{t("settings.access.copyInviteNow")}</p>
            <div className="flex gap-2">
              <Input readOnly value={lastInviteUrl} className="font-mono text-xs" />
              <Button
                variant="outline"
                size="icon"
                aria-label={t("settings.access.copyInvite")}
                onClick={() => {
                  void navigator.clipboard.writeText(lastInviteUrl);
                  toast.success(t("settings.access.inviteCopied"));
                }}
              ><Copy className="size-4" /></Button>
            </div>
          </div>
        )}
        <div className="divide-y rounded-md border">
          {(invites.data ?? []).map((invite) => (
            <div key={invite.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <div>
                <p>{invite.email}</p>
                <p className="text-xs text-muted-foreground">
                  {invite.active ? t("settings.access.activeInvite") : t("settings.access.inactiveInvite")}
                  {" · "}{new Date(invite.expiresAt).toLocaleDateString()}
                </p>
              </div>
              {invite.active && (
                <Button variant="outline" size="sm" onClick={() => revokeInvite.mutate(invite.id, { onError: reportFailure })}>
                  {t("settings.access.revoke")}
                </Button>
              )}
            </div>
          ))}
        </div>
      </SettingsSectionCard>
    </div>
  );
}

function EntitlementRow({ entitlement }: { entitlement: AIEntitlement }) {
  const { t } = useTranslation();
  const update = useUpdateAIEntitlement();
  const [state, setState] = React.useState(entitlement.state);
  const [limit, setLimit] = React.useState(String(entitlement.monthlyLimitUnits ?? 100));

  return (
    <div className="grid gap-3 border-b px-3 py-3 last:border-b-0 lg:grid-cols-[minmax(12rem,1fr)_9rem_8rem_auto] lg:items-center">
      <div><p className="font-medium">{entitlement.userName}</p><p className="text-xs text-muted-foreground">{entitlement.userEmail}</p></div>
      <Select value={state} onValueChange={(value: AIEntitlement["state"]) => setState(value)}>
        <SelectTrigger><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="disabled">{t("settings.access.disabled")}</SelectItem>
          <SelectItem value="limited">{t("settings.access.limited")}</SelectItem>
          <SelectItem value="unlimited">{t("settings.access.unlimited")}</SelectItem>
        </SelectContent>
      </Select>
      <Input
        type="number"
        min={1}
        aria-label={t("settings.access.monthlyCredits")}
        value={limit}
        disabled={state !== "limited"}
        onChange={(event) => setLimit(event.target.value)}
      />
      <Button
        size="sm"
        disabled={update.isPending || (state === "limited" && Number(limit) < 1)}
        onClick={() => update.mutate({
          userId: entitlement.userId,
          state,
          monthlyLimitUnits: state === "limited" ? Number(limit) : null,
        }, { onError: reportFailure })}
      >{t("common.save")}</Button>
      <p className="text-xs text-muted-foreground lg:col-start-2 lg:col-span-3">
        {entitlement.usedUnits} {t("settings.access.creditsUsed")}
        {entitlement.remainingUnits != null ? ` · ${entitlement.remainingUnits} ${t("settings.access.remaining")}` : ""}
      </p>
    </div>
  );
}

export function AdminPeopleSection() {
  const { t } = useTranslation();
  const entitlements = useAIEntitlements();
  return (
    <SettingsSectionCard
      title={t("settings.sections.adminPeople.title")}
      description={t("settings.sections.adminPeople.description")}
    >
      <div className="overflow-hidden rounded-md border">
        {(entitlements.data ?? []).map((entitlement) => <EntitlementRow key={entitlement.userId} entitlement={entitlement} />)}
        {!entitlements.isLoading && (entitlements.data?.length ?? 0) === 0 && (
          <p className="p-3 text-sm text-muted-foreground">{t("settings.access.noPeople")}</p>
        )}
      </div>
    </SettingsSectionCard>
  );
}

function CapabilityPolicyRow({ policy }: { policy: CapabilityCostPolicy }) {
  const { t } = useTranslation();
  const update = useUpdateCapabilityCostPolicy();
  const [classification, setClassification] = React.useState<
    "unclassified" | "unmetered" | "ai"
  >(policy.classification);
  const [cost, setCost] = React.useState(String(policy.costUnits ?? (classification === "ai" ? 1 : 0)));

  return (
    <div className="grid gap-3 border-b px-3 py-3 last:border-b-0 lg:grid-cols-[minmax(14rem,1fr)_10rem_7rem_auto] lg:items-center">
      <div>
        <p className="font-medium">{policy.displayName ?? policy.capabilityId}</p>
        <p className="text-xs text-muted-foreground">{policy.extensionId} · {policy.version} · {policy.surface}</p>
      </div>
      <Select
        value={classification}
        onValueChange={(value: "unclassified" | "unmetered" | "ai") => {
          setClassification(value);
          setCost(value === "ai" ? String(Math.max(Number(cost) || 1, 1)) : "0");
        }}
      >
        <SelectTrigger><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="unclassified" disabled>{t("settings.access.unclassified")}</SelectItem>
          <SelectItem value="unmetered">{t("settings.access.unmetered")}</SelectItem>
          <SelectItem value="ai">{t("settings.access.aiMetered")}</SelectItem>
        </SelectContent>
      </Select>
      <Input type="number" min={classification === "ai" ? 1 : 0} disabled={classification !== "ai"} value={cost} onChange={(event) => setCost(event.target.value)} />
      <Button
        size="sm"
        disabled={update.isPending || classification === "unclassified" || (classification === "ai" && Number(cost) < 1)}
        onClick={() => {
          if (classification === "unclassified") return;
          update.mutate({ capabilityDefinitionId: policy.capabilityDefinitionId, classification, costUnits: classification === "ai" ? Number(cost) : 0 }, { onError: reportFailure });
        }}
      >{policy.classification === "unclassified" ? t("settings.access.classify") : t("common.save")}</Button>
    </div>
  );
}

export function AIControlsSection() {
  const { t } = useTranslation();
  const policy = usePlatformPolicy();
  const updatePolicy = useUpdatePlatformPolicy();
  const capabilities = useCapabilityCostPolicies();
  const usage = useAIUsage();
  const unclassified = (capabilities.data ?? []).filter((item) => item.classification === "unclassified").length;

  return (
    <div className="space-y-4">
      <SettingsSectionCard title={t("settings.access.aiControls")} description={t("settings.access.aiControlsDescription")}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <Label htmlFor="ai-controls-enabled">{t("settings.access.enforceCredits")}</Label>
            <p className="text-xs text-muted-foreground">{t("settings.access.weightedNotCurrency")}</p>
          </div>
          <Switch
            id="ai-controls-enabled"
            checked={policy.data?.effectiveAiControlsEnabled ?? false}
            disabled={policy.isLoading || policy.data?.aiControlsLocked || updatePolicy.isPending || unclassified > 0}
            onCheckedChange={(checked) => updatePolicy.mutate({ aiControlsEnabled: checked }, { onError: reportFailure })}
          />
        </div>
        {unclassified > 0 && <p className="text-sm text-destructive">{t("settings.access.unclassifiedWarning", { count: unclassified })}</p>}
      </SettingsSectionCard>

      <SettingsSectionCard title={t("settings.access.capabilityCosts")} description={t("settings.access.capabilityCostsDescription")}>
        <div className="overflow-hidden rounded-md border">
          {(capabilities.data ?? []).map((item) => <CapabilityPolicyRow key={item.capabilityDefinitionId} policy={item} />)}
          {!capabilities.isLoading && (capabilities.data?.length ?? 0) === 0 && <p className="p-3 text-sm text-muted-foreground">{t("settings.access.noCapabilities")}</p>}
        </div>
      </SettingsSectionCard>

      <SettingsSectionCard title={t("settings.access.usageAudit")} description={t("settings.access.usageAuditDescription")}>
        <p className="text-xl leading-6 font-medium">{usage.data?.totalUnits ?? 0}</p>
        <p className="text-xs text-muted-foreground">{t("settings.access.currentMonthCredits")}</p>
        <div className="divide-y rounded-md border">
          {(usage.data?.charges ?? []).slice(0, 10).map((charge) => (
            <div key={charge.id} className="flex justify-between gap-3 px-3 py-2 text-xs">
              <span>{charge.userEmail} · {charge.capabilityId}</span><span>{charge.units}</span>
            </div>
          ))}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
