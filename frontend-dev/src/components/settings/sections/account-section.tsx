import { toast } from "sonner";
import { AxiosError } from "axios";
import { AlertCircle } from "lucide-react";

import { DangerZoneSection } from "@/components/settings/sections/danger-zone-section";
import { ProfileSection } from "@/components/settings/sections/profile-section";
import { IfSetting } from "@/components/if-setting";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import api from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export function AccountSection() {
  const { user } = useAuth();

  const resendVerification = async () => {
    try {
      const response = await api.post("/auth/resend-verification");
      toast.success("Verification email sent", {
        description: String(response.data?.detail ?? "Check your inbox for a verification email."),
      });
    } catch (error) {
      const axiosError = error as AxiosError<{ detail?: string }>;
      toast.error("Could not resend verification email", {
        description:
          axiosError.response?.data?.detail ?? "Try again later.",
      });
    }
  };

  return (
    <div className="space-y-4">
      <ProfileSection />
      <IfSetting setting="features.emailEnabled" scope="local">
        {!user?.isVerified && (
          <SettingsSectionCard
            title="Email verification"
            description="Manage account verification emails."
          >
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Email not verified</AlertTitle>
              <AlertDescription>
                Your email address is not verified. Please verify your email address to continue.
              </AlertDescription>
            </Alert>
            <Button variant="outline" onClick={() => void resendVerification()}>
              Resend verification email
            </Button>
          </SettingsSectionCard>
        )}
      </IfSetting>
      <DangerZoneSection />
    </div>
  );
}
