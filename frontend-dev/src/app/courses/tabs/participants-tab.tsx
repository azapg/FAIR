import {useTranslation} from "react-i18next";

type Instructor = {
  id: string;
  name: string;
  email: string;
  role: string;
};

export function ParticipantsTab({instructor}: { instructor?: Instructor }) {
  const {t} = useTranslation();

  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <h3 className="text-lg font-semibold mb-2">{t("courses.instructor")}</h3>
        {instructor ? (
          <div className="space-y-1 text-sm">
            <p className="font-medium">{instructor.name}</p>
            <p className="text-muted-foreground">{instructor.email}</p>
            <p className="text-muted-foreground capitalize">{instructor.role}</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("participants.noInstructor")}</p>
        )}
      </div>

      <div className="rounded-lg border p-4">
        <h3 className="text-lg font-semibold mb-2">{t("participants.students")}</h3>
        <p className="text-sm text-muted-foreground">{t("participants.noStudents")}</p>
      </div>
    </div>
  );
}
