import { Button } from "@/components/ui/button";
import { Hash, MoreVertical, RefreshCw } from "lucide-react";
import { TFunction } from "i18next";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

interface EnrollmentControlsProps {
  enrollmentCode: string | null | undefined;
  isEnrollmentEnabled: boolean;
  onToggle: (next: boolean) => Promise<void>;
  onResetCode: () => Promise<void>;
  isTogglePending: boolean;
  isResetPending: boolean;
  t: TFunction;
}

export function EnrollmentControls({
  enrollmentCode,
  isEnrollmentEnabled,
  onToggle,
  onResetCode,
  isTogglePending,
  isResetPending,
  t,
}: EnrollmentControlsProps) {
  return (
    <div className="px-8 pb-3 w-full md:w-1/2 lg:w-1/3">
      <Card className="bg-muted gap-0 pt-3">
        <CardHeader className="flex flex-row items-center justify-between my-0 py-0">
          <span>{t("courses.classCode")}</span>
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                disabled={isResetPending}
                onClick={() => onResetCode()}
              >
                <RefreshCw />
                {t("courses.resetCode")}
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={isTogglePending}
                onClick={() => onToggle(!isEnrollmentEnabled)}
              >
                <Hash />
                {t("courses.selfEnrollment")}
                <DropdownMenuCheckboxItem checked={isEnrollmentEnabled} />
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardHeader>

        <CardContent className="pb-2">
          {isEnrollmentEnabled ? (
            <span className="font-mono text-2xl lg:text-3xl tracking-widest">
              {enrollmentCode}
            </span>
          ) : (
            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted-foreground">{t("courses.selfEnrollmentDisabled")}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onToggle(true)}
              >
                {t("common.enable")}
              </Button>
            </div>
          )}
        </CardContent>

        <CardFooter className="text-xs text-muted-foreground max-w-xl">
          {isEnrollmentEnabled && t("courses.selfEnrollmentHint")}
        </CardFooter>
      </Card>
    </div>
  );
}
