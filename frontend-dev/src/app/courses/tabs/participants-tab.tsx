import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Ellipsis } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Instructor = {
  id: string;
  name: string;
  email: string;
  role: string;
};

export function ParticipantsTab({ instructor }: { instructor?: Instructor }) {
  const { t } = useTranslation();
  const instructors = useMemo(
    () => (instructor ? [instructor] : []),
    [instructor],
  );

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold mb-3">
        {t("participants.instructors")}
      </h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("courses.instructor")}</TableHead>
            <TableHead>{t("auth.email")}</TableHead>
            <TableHead>{t("courses.description")}</TableHead>
            <TableHead className="w-12 text-right">
              {t("actions.courseActions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {instructors.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-sm text-muted-foreground">
                {t("participants.noInstructor")}
              </TableCell>
            </TableRow>
          ) : (
            instructors.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="flex items-center gap-2">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>
                      {item.name?.[0]?.toUpperCase() ?? "I"}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col">
                    <span className="font-medium">{item.name}</span>
                    <span className="text-xs text-muted-foreground capitalize">
                      {item.role}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {item.email}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {t("participants.instructorRole")}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger className="ml-auto flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                      <Ellipsis className="h-4 w-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem disabled>View profile</DropdownMenuItem>
                      <DropdownMenuItem disabled>
                        {t("common.edit")}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <h2 className="text-xl font-semibold mb-2">
        {t("participants.students")}
      </h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("participants.students")}</TableHead>
            <TableHead>{t("auth.email")}</TableHead>
            <TableHead>{t("courses.description")}</TableHead>
            <TableHead className="w-12 text-right">
              {t("actions.courseActions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell colSpan={4} className="text-sm text-muted-foreground">
              {t("participants.noStudents")}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
