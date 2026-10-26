import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  EnrollmentControls,
  type EnrollmentControlsProps,
} from "./enrollment-controls";

function mount(props: Partial<EnrollmentControlsProps> = {}) {
  const onToggle = vi.fn().mockResolvedValue(undefined);
  const onResetCode = vi.fn().mockResolvedValue(undefined);
  const view = render(
    <EnrollmentControls
      enrollmentCode="F7NB"
      isEnrollmentEnabled
      onToggle={onToggle}
      onResetCode={onResetCode}
      isTogglePending={false}
      isResetPending={false}
      {...props}
    />,
  );
  return { ...view, onToggle, onResetCode };
}
async function openOptions() {
  fireEvent.keyDown(
    screen.getByRole("button", { name: "Class code options" }),
    { key: "ArrowDown" },
  );
  await screen.findByRole("menuitem", { name: "Rotate code" });
}

describe("Enrollment controls", () => {
  afterEach(cleanup);
  it("requires confirmation before rotating the real code", async () => {
    const { onResetCode } = mount();
    await openOptions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Rotate code" }));
    expect(onResetCode).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Rotate code" }));
    await waitFor(() => expect(onResetCode).toHaveBeenCalledOnce());
    await waitFor(() =>
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
    );
  });
  it("allows disabling from the code menu and re-enabling from its disabled state", async () => {
    const { onToggle, unmount } = mount();
    await openOptions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Disable code" }));
    expect(onToggle).toHaveBeenCalledWith(false);
    unmount();
    const disabled = mount({ isEnrollmentEnabled: false });
    expect(screen.queryByText("F7NB")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enable code" }));
    expect(disabled.onToggle).toHaveBeenCalledWith(true);
  });
  it("keeps the confirmation open if rotation fails", async () => {
    const onResetCode = vi.fn().mockRejectedValue(new Error("Offline"));
    mount({ onResetCode });
    await openOptions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Rotate code" }));
    fireEvent.click(screen.getByRole("button", { name: "Rotate code" }));
    await waitFor(() => expect(onResetCode).toHaveBeenCalledOnce());
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });
});
