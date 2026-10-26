import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react";
import {
  AiLearningIcon,
  Analytics01Icon,
  Atom01Icon,
  Basketball01Icon,
  BankIcon,
  Book02Icon,
  BookOpen01Icon,
  BrainIcon,
  Briefcase01Icon,
  Building01Icon,
  Calculator01Icon,
  Camera01Icon,
  Chart01Icon,
  Chemistry02Icon,
  CodeIcon,
  Coins01Icon,
  ComputerIcon,
  CourtHouseIcon,
  DnaIcon,
  Dumbbell01Icon,
  EarthIcon,
  FootballIcon,
  FunctionIcon,
  Globe02Icon,
  HealthIcon,
  HeartCheckIcon,
  LanguageSkillIcon,
  Leaf01Icon,
  LegalDocument01Icon,
  MapsIcon,
  MarketingIcon,
  MicroscopeIcon,
  Mortarboard01Icon,
  MusicNote01Icon,
  Notebook02Icon,
  PaintBrush01Icon,
  PencilEdit01Icon,
  Plant01Icon,
  PuzzleIcon,
  Robot01Icon,
  Rocket01Icon,
  Stethoscope02Icon,
  TeacherIcon,
  Telescope01Icon,
  TestTube01Icon,
  TranslationIcon,
  Video01Icon,
} from "@hugeicons/core-free-icons";

export const DEFAULT_COURSE_ICON_KEY = "book-open";

export type CourseIconOption = {
  key: string;
  labelKey: string;
  keywords: string[];
  icon: IconSvgElement;
};

const option = (key: string, icon: IconSvgElement, keywords: string[]): CourseIconOption => ({
  key,
  icon,
  keywords,
  labelKey: `courses.icons.${key}`,
});

export const COURSE_ICON_OPTIONS = [
  option("book-open", BookOpen01Icon, ["book", "reading", "general", "libro", "lectura"]),
  option("notebook", Notebook02Icon, ["notes", "writing", "cuaderno", "notas"]),
  option("writing", PencilEdit01Icon, ["pencil", "essay", "escritura", "ensayo"]),
  option("graduation", Mortarboard01Icon, ["school", "degree", "graduación", "escuela"]),
  option("teaching", TeacherIcon, ["teacher", "education", "docencia", "educación"]),
  option("mathematics", FunctionIcon, ["math", "algebra", "calculus", "matemáticas", "cálculo"]),
  option("calculator", Calculator01Icon, ["numbers", "accounting", "números", "contabilidad"]),
  option("statistics", Chart01Icon, ["chart", "data", "estadística", "datos"]),
  option("analytics", Analytics01Icon, ["data", "research", "análisis", "investigación"]),
  option("physics", Atom01Icon, ["atom", "science", "física", "ciencia"]),
  option("chemistry", Chemistry02Icon, ["science", "molecule", "química", "ciencia"]),
  option("laboratory", TestTube01Icon, ["lab", "experiment", "laboratorio", "experimento"]),
  option("biology", DnaIcon, ["dna", "genetics", "biología", "genética"]),
  option("microscopy", MicroscopeIcon, ["science", "research", "microscopio", "investigación"]),
  option("astronomy", Telescope01Icon, ["space", "stars", "astronomía", "estrellas"]),
  option("geography", Globe02Icon, ["world", "countries", "geografía", "mundo"]),
  option("maps", MapsIcon, ["map", "location", "mapas", "ubicación"]),
  option("earth-science", EarthIcon, ["planet", "geology", "tierra", "geología"]),
  option("languages", LanguageSkillIcon, ["language", "grammar", "idiomas", "gramática"]),
  option("translation", TranslationIcon, ["language", "interpretation", "traducción", "idiomas"]),
  option("literature", Book02Icon, ["books", "novel", "literatura", "novela"]),
  option("art", PaintBrush01Icon, ["painting", "creative", "arte", "pintura"]),
  option("music", MusicNote01Icon, ["audio", "theory", "música", "sonido"]),
  option("photography", Camera01Icon, ["camera", "media", "fotografía", "cámara"]),
  option("film", Video01Icon, ["video", "cinema", "cine", "película"]),
  option("design", PuzzleIcon, ["creative", "visual", "diseño", "creativo"]),
  option("programming", CodeIcon, ["code", "software", "programación", "código"]),
  option("computing", ComputerIcon, ["computer", "technology", "computación", "tecnología"]),
  option("artificial-intelligence", AiLearningIcon, ["ai", "machine learning", "ia", "aprendizaje"]),
  option("robotics", Robot01Icon, ["robot", "engineering", "robótica", "ingeniería"]),
  option("psychology", BrainIcon, ["mind", "behavior", "psicología", "mente"]),
  option("business", Briefcase01Icon, ["management", "work", "negocios", "gestión"]),
  option("marketing", MarketingIcon, ["advertising", "brand", "mercadeo", "publicidad"]),
  option("economics", Coins01Icon, ["finance", "money", "economía", "finanzas"]),
  option("finance", BankIcon, ["markets", "accounting", "finanzas", "mercados"]),
  option("law", CourtHouseIcon, ["legal", "justice", "derecho", "justicia"]),
  option("legal-studies", LegalDocument01Icon, ["law", "policy", "leyes", "política"]),
  option("architecture", Building01Icon, ["building", "construction", "arquitectura", "construcción"]),
  option("health", HealthIcon, ["wellness", "medicine", "salud", "bienestar"]),
  option("medicine", Stethoscope02Icon, ["doctor", "clinical", "medicina", "clínico"]),
  option("cardiology", HeartCheckIcon, ["heart", "health", "cardiología", "corazón"]),
  option("sports", FootballIcon, ["sport", "team", "deportes", "equipo"]),
  option("basketball", Basketball01Icon, ["sport", "team", "baloncesto", "deporte"]),
  option("fitness", Dumbbell01Icon, ["exercise", "gym", "ejercicio", "gimnasio"]),
  option("environment", Leaf01Icon, ["nature", "ecology", "ambiente", "ecología"]),
  option("botany", Plant01Icon, ["plants", "nature", "botánica", "plantas"]),
  option("space", Rocket01Icon, ["rocket", "aerospace", "espacio", "cohete"]),
] as const satisfies readonly CourseIconOption[];

const COURSE_ICONS_BY_KEY = new Map(COURSE_ICON_OPTIONS.map((item) => [item.key, item]));

export function getCourseIconOption(iconKey?: string | null): CourseIconOption {
  return COURSE_ICONS_BY_KEY.get(iconKey ?? "") ?? COURSE_ICON_OPTIONS[0];
}

export function CourseIcon({
  iconKey,
  className,
  size = 24,
}: {
  iconKey?: string | null;
  className?: string;
  size?: number;
}) {
  return (
    <HugeiconsIcon
      aria-hidden="true"
      className={className}
      icon={getCourseIconOption(iconKey).icon}
      size={size}
      strokeWidth={1.7}
    />
  );
}
