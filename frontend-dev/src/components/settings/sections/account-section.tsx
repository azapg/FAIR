import { DangerZoneSection } from "@/components/settings/sections/danger-zone-section";
import { ProfileSection } from "@/components/settings/sections/profile-section";

export function AccountSection() {
  return (
    <div className="space-y-4">
      <ProfileSection />
      <DangerZoneSection />
    </div>
  );
}
