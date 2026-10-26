import { useEffect, useState } from "react";
import { Check, Copy, MoreHorizontal, RefreshCw, Ban } from "lucide-react";
import type { TFunction } from "i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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

export interface EnrollmentControlsProps {
  enrollmentCode: string | null | undefined;
  isEnrollmentEnabled: boolean;
  onToggle: (next: boolean) => Promise<void>;
  onResetCode: () => Promise<void>;
  isTogglePending: boolean;
  isResetPending: boolean;
  t?: TFunction;
}

export function EnrollmentControls({
  enrollmentCode,
  isEnrollmentEnabled,
  onToggle,
  onResetCode,
  isTogglePending,
  isResetPending,
}: EnrollmentControlsProps) {
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [copied, setCopied] = useState(false);
  const pending = isTogglePending || isResetPending;
  useEffect(() => {
    setCopied(false);
  }, [enrollmentCode]);

  async function copyCode() {
    if (!enrollmentCode) return;
    try {
      await navigator.clipboard.writeText(enrollmentCode);
      setCopied(true);
    } catch {
      toast.error(
        "Could not copy the class code. You can select and copy it directly.",
      );
    }
  }

  return (
    <>
      <Card className="w-full gap-3 border-0 bg-muted/70 py-4 shadow-none">
        <CardHeader className="flex flex-row items-center justify-between px-4">
          <CardTitle className="text-xs font-normal text-muted-foreground">
            Class code
          </CardTitle>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-xs"
                aria-label="Class code options"
                title="Class code options"
                disabled={pending}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuGroup>
                <DropdownMenuItem
                  disabled={!isEnrollmentEnabled || !enrollmentCode}
                  onSelect={() => setConfirmRotate(true)}
                >
                  <RefreshCw /> Rotate code
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() => {
                    void onToggle(!isEnrollmentEnabled).catch(() => {});
                  }}
                >
                  {isEnrollmentEnabled ? <Ban /> : <Check />}
                  {isEnrollmentEnabled ? "Disable code" : "Enable code"}
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardHeader>
        <CardContent className="px-4">
          {isEnrollmentEnabled ? (
            <div className="flex items-center justify-between gap-2">
              <span
                className={
                  enrollmentCode
                    ? "select-all font-mono text-2xl tracking-widest lg:text-3xl"
                    : "text-sm text-muted-foreground"
                }
              >
                {enrollmentCode ?? "Unavailable"}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={copied ? "Class code copied" : "Copy class code"}
                title="Copy class code"
                disabled={!enrollmentCode}
                onClick={copyCode}
              >
                {copied ? <Check /> : <Copy />}
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-start gap-2">
              <span className="text-sm text-muted-foreground">Disabled</span>
              <Button
                variant="link"
                size="sm"
                className="px-0"
                disabled={pending}
                onClick={() => {
                  void onToggle(true).catch(() => {});
                }}
              >
                Enable code
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      <AlertDialog open={confirmRotate} onOpenChange={setConfirmRotate}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rotate class code?</AlertDialogTitle>
            <AlertDialogDescription>
              Students will need the new code to join. The previous code will
              stop working. Existing students will stay enrolled.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={pending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={pending}
              onClick={(event) => {
                event.preventDefault();
                void onResetCode()
                  .then(() => {
                    setCopied(false);
                    setConfirmRotate(false);
                  })
                  .catch(() => {});
              }}
            >
              {isResetPending ? "Rotating…" : "Rotate code"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
