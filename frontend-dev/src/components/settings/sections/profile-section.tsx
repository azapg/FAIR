import { AxiosError } from "axios";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/auth-context";
import UserAvatar from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ResponsiveDialogContent } from "@/components/ui/responsive-dialog";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import api from "@/lib/api";

type PasswordError = { detail?: string };

type ChangePasswordDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function ChangePasswordDialog({ open, onOpenChange }: ChangePasswordDialogProps) {
  const { t } = useTranslation();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const resetForm = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setError(null);
    setSubmitting(false);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
    if (!nextOpen) resetForm();
  };

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setError(t("settings.sections.profile.passwordsMustMatch"));
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await api.post("/auth/change-password", { currentPassword, newPassword });
      toast.success(t("settings.sections.profile.passwordChanged"), {
        description: t("settings.sections.profile.passwordChangedDescription"),
      });
      handleOpenChange(false);
    } catch (err) {
      const axiosError = err as AxiosError<PasswordError>;
      setError(
        axiosError.response?.data?.detail ??
          t("settings.sections.profile.changePasswordFailed"),
      );
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <ResponsiveDialogContent>
        <DialogHeader>
          <DialogTitle>{t("settings.sections.profile.changePasswordTitle")}</DialogTitle>
          <DialogDescription>
            {t("settings.sections.profile.changePasswordDescription")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit}>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="current-password">{t("auth.currentPassword")}</FieldLabel>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
                disabled={submitting}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-password">{t("auth.newPassword")}</FieldLabel>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                disabled={submitting}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="confirm-password">{t("auth.confirmPassword")}</FieldLabel>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                disabled={submitting}
              />
            </Field>
            {error ? (
              <FieldDescription role="alert" className="text-destructive">
                {error}
              </FieldDescription>
            ) : null}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={submitting}
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting
                  ? t("settings.sections.profile.changingPassword")
                  : t("settings.sections.profile.changePassword")}
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </ResponsiveDialogContent>
    </Dialog>
  );
}

export function ProfileSection() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [random, setRandom] = useState<number | null>(null);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const userName = user?.name ?? t("header.profile");
  const userEmail = user?.email ?? "";

  const regenerateAvatar = () => {
    setRandom((prev) => (prev === null ? 1 : prev + 1)  );
  }


  return (
    <SettingsSectionCard
      title={t("settings.sections.profile.title")}
      description={t("settings.sections.profile.description")}
    >
      <div className="flex flex-col justify-center rounded-lg gap-2">
        <div className="flex gap-4">
          <UserAvatar size="xl" avatarSrc={null} username={userName + (random ? ` (${random})` : "")} />
          <div className="space-y-2">
            {t("settings.sections.profile.yourName")}
            <Input value={userName} disabled />
          </div>
        </div>
        <div>
          <Button variant="link" className="p-0 h-auto text-blue-500">{t("settings.sections.profile.addProfilePictureAction")}</Button> {t("common.or")} <Button variant="link" className="p-0 h-auto text-blue-500" onClick={regenerateAvatar}>{t("settings.sections.profile.generateProfilePictureAction")}</Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-medium">{t("settings.fields.email")}</span>
          <span className="text-sm text-muted-foreground">{userEmail}</span>
        </div>
        <Button id="settings-profile-email" variant="outline">
          {t("settings.sections.profile.changeEmail")}
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{t("settings.fields.password")}</span>
        <Button
          id="settings-profile-password"
          variant="outline"
          onClick={() => setChangePasswordOpen(true)}
        >
          {t("settings.sections.profile.changePassword")}
        </Button>
      </div>

      <ChangePasswordDialog
        open={changePasswordOpen}
        onOpenChange={setChangePasswordOpen}
      />
    </SettingsSectionCard>
  );
}
