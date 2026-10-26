import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { apiPost, apiGet, toastSuccess } = vi.hoisted(() => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ default: { post: apiPost, get: apiGet } }));
vi.mock("@/hooks/use-system-config", () => ({
  useSystemConfig: () => ({ data: { authentication: { providers: ['google'] } } }),
}));
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }));
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: 'test-user',
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
        "auth.connectGoogle": "Connect Google",
        "auth.continueWithGoogle": "Continue with Google",
        "auth.connectGoogleDescription": "Confirm your password, then choose Google.",
        "auth.googleLinkFailed": "Check your password and try again.",
        "auth.googleConnected": "Connected",
        "common.cancel": "Cancel",
        "common.or": "or",
      })[key] ?? key,
  }),
}));

import { ProfileSection } from "./profile-section";

function renderProfile() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <ProfileSection />
  </QueryClientProvider>);
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProfileSection password change", () => {
  beforeEach(() => {
    apiGet.mockResolvedValue({ data: { hasPassword: true, providers: [] } });
    apiPost.mockResolvedValue({ data: { detail: "Password changed successfully" } });
  });

  it("opens the change-password form and submits the password fields", async () => {
    renderProfile();

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
    renderProfile();
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

  it("connects Google only after confirming the current password", async () => {
    apiPost.mockRejectedValueOnce(new Error('incorrect password'));
    renderProfile();
    fireEvent.click(await screen.findByRole('button', { name: 'Connect Google' }));
    fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'confirmation' } });
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith('/auth/oidc/google/link', { currentPassword: 'confirmation' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Check your password');
  });

  it("shows a Google-only account without a change-password action", async () => {
    apiGet.mockResolvedValue({ data: { hasPassword: false, providers: ['google'] } });
    renderProfile();
    expect(await screen.findByText('Connected')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Change password' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Connect Google' })).not.toBeInTheDocument();
  });
});
