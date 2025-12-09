import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Languages } from "lucide-react";
import { IconSpain, IconUnitedStates } from "nucleo-flags"

const languages = [
  { code: "en", name: "English", flag: <IconUnitedStates /> },
  { code: "es", name: "Español", flag: <IconSpain /> },
];

export function LanguageSelect({slug}: {slug: string}) {
  // Extract the current language code from the start of the slug
  const currentLang = slug.split('/')[0];

  const changeLanguage = (langCode: string) => {
    if (langCode === currentLang) return;

    // Replace the current language code with the new one at the start of the slug
    const newSlug = slug.replace(new RegExp(`^${currentLang}`), langCode);

    // Navigate to the new URL
    window.location.href = `/docs/${newSlug}`;
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Select language">
          <Languages className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {languages.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onClick={() => changeLanguage(lang.code)}
            className={`cursor-pointer ${lang.code === currentLang ? "bg-accent" : ""}`}
          >
            <span className="mr-2">{lang.flag}</span>
            {lang.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
