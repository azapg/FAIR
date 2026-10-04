import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { apiPost, toastSuccess } = vi.hoisted(() => ({
  apiPost: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ default: { post: apiPost } }));
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }));
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      name: "Test User",
      email: "test@example.com",
    },
  }),
}));
vi.mock("sonner", () => ({ toast: { success: toastSuccess } }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "header.profile": "Profile",
        "settings.sections.profile.title": "Profile",
        "settings.sections.profile.description": "Profile controls.",
        "settings.sections.profile.yourName": "Your name",
        "settings.sections.profile.addProfilePictureAction": "Add a profile picture",
        "settings.sections.profile.generateProfilePictureAction": "generate a random face.",
        "settings.sections.profile.changeEmail": "Change email",
        "settings.sections.profile.changePassword": "Change password",
        "settings.sections.profile.changePasswordTitle": "Change your password",
        "settings.sections.profile.changePasswordDescription": "Enter your current password.",
        "settings.sections.profile.changingPassword": "Changing password...",
        "settings.sections.profile.passwordsMustMatch": "New passwords must match.",
        "settings.sections.profile.passwordChanged": "Password changed",
        "settings.sections.profile.passwordChangedDescription": "Updated successfully.",
        "settings.sections.profile.changePasswordFailed": "Unable to change your password.",
        "settings.fields.email": "Email",
        "settings.fields.password": "Password",
        "auth.currentPassword": "Current password",
        "auth.newPassword": "New password",
        "auth.confirmPassword": "Confirm password",
        "common.cancel": "Cancel",
        "common.or": "or",
      })[key] ?? key,
  }),
}));

import { ProfileSection } from "./profile-section";

afterEach(() => {
  vi.clearAllMocks();
});

describe("ProfileSection password change", () => {
  beforeEach(() => {
    apiPost.mockResolvedValue({ data: { detail: "Password changed successfully" } });
  });

  it("opens the change-password form and submits the password fields", async () => {
    render(<ProfileSection />);

    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(screen.getByRole("dialog", { name: "Change your password" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "old_password" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new_password_123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "new_password_123" },
    });
    fireEvent.submit(screen.getByRole("dialog").querySelector("form")!);

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/auth/change-password", {
        currentPassword: "old_password",
        newPassword: "new_password_123",
      }),
    );
    expect(toastSuccess).toHaveBeenCalled();
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Change your password" })).not.toBeInTheDocument(),
    );
  });

  it("does not submit when the new passwords do not match", () => {
    render(<ProfileSection />);
    fireEvent.click(document.getElementById("settings-profile-password")!);

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "old_password" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new_password_123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "different_password" },
    });
    fireEvent.submit(screen.getByRole("dialog").querySelector("form")!);

    expect(screen.getByRole("alert")).toHaveTextContent("New passwords must match.");
    expect(apiPost).not.toHaveBeenCalled();
  });
});
