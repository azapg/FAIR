import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import { useEffect, useState } from "react";
import type { ComponentProps } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  FileText,
  Plus,
  LogOut,
  User,
  Home,
  SearchIcon,
  InboxIcon,
  X,
  SettingsIcon,
  MessageCircleQuestionMarkIcon,
  ClipboardList,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/auth-context";
import { useIsMobile } from "@/hooks/use-mobile";
import { useCourses } from "@/hooks/use-courses";
import { useAllAssignments } from "@/hooks/use-assignments";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import UserAvatar from "@/components/user-avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SettingsDialog } from "@/components/settings/settings-dialog";
import { usePreferenceSettings } from "@/hooks/use-preference-settings";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Button } from "@/components/ui/button";

const languages = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
];

function InboxEmptyState() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language;

  return (
    <Empty className="h-full rounded-none border-0 p-6 md:p-8">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <InboxIcon className="size-5" />
        </EmptyMedia>
        <EmptyTitle>{t("inbox.empty.title")}</EmptyTitle>
        <EmptyDescription>{t("inbox.empty.description")}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <a
          href={`/docs/${currentLang}/platform/workflows`}
          target="_blank"
          rel="noreferrer"
          className="text-muted-foreground text-sm underline underline-offset-4 hover:text-foreground"
        >
          {t("common.learnMore")}
        </a>
      </EmptyContent>
    </Empty>
  );
}

function NavMain({
  isInboxOpen,
  onInboxToggle,
}: {
  isInboxOpen: boolean;
  onInboxToggle: () => void;
}) {
  const { t } = useTranslation();
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip={t("nav.home")}>
          <Link to="/">
            <Home />
            <span>{t("nav.home")}</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>

      {/*search*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip={t("nav.search")}>
          <Link to="/search">
            <SearchIcon />
            <span>{t("nav.search")}</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>

      <SidebarMenuItem>
        <SidebarMenuButton
          tooltip={t("nav.inbox")}
          onClick={onInboxToggle}
          isActive={isInboxOpen}
        >
          <InboxIcon />
          <span>{t("nav.inbox")}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

function NavSecondary({ onSettingsClick }: { onSettingsClick: () => void }) {
  const { t } = useTranslation();
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip={t("nav.rubrics")}>
          <Link to="/rubrics">
            <ClipboardList />
            <span>{t("nav.rubrics")}</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton tooltip={t("nav.settings")} onClick={onSettingsClick}>
          <SettingsIcon />
          <span>{t("nav.settings")}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
      {/*Help*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip={t("nav.help")}>
          <a href="https://docs.fairgradeproject.org" target="_blank" rel="noreferrer">
            <MessageCircleQuestionMarkIcon />
            <span>{t("nav.help")}</span>
          </a>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

export function AppSidebar({
  side = "left",
  className,
  style,
  ...props
}: ComponentProps<typeof Sidebar> & {
  side?: "left" | "right";
}) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { user: authUser, isAuthenticated, logout } = useAuth();
  const { effectiveTheme, setThemePreference, setLanguagePreference } =
    usePreferenceSettings();
  const isMobile = useIsMobile();
  const { data: courses = [] } = useCourses();
  const { data: assignments = [] } = useAllAssignments(isAuthenticated);
  const { setOpen, state, isMobile: isSidebarMobile, openMobile } = useSidebar();
  const [showAllAssignments, setShowAllAssignments] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [coursesOpen, setCoursesOpen] = useState(true);
  const [assignmentsOpen, setAssignmentsOpen] = useState(false);

  useEffect(() => {
    if (state !== "expanded") {
      setInboxOpen(false);
    }
  }, [state]);

  useEffect(() => {
    if (isSidebarMobile && !openMobile) {
      setInboxOpen(false);
    }
  }, [isSidebarMobile, openMobile]);

  const displayTitle = t("header.title");
  const userName = authUser?.name || t("header.profile");
  const userEmail = authUser?.email || "user@example.com";

  const currentLanguage =
    languages.find((lang) =>
      i18n.language?.toLowerCase().startsWith(lang.code),
    ) ?? languages[0];

  const sidebarStyle = {
    ...(style ?? {}),
    ["--sidebar-width" as string]: !isSidebarMobile && inboxOpen ? "40rem" : "20rem",
    ["--app-sidebar-main-width" as string]: "20rem",
  } as React.CSSProperties;

  return (
    <Sidebar
      side={side}
      collapsible="icon"
      className={className}
      style={sidebarStyle}
      {...props}
    >
      <div className="flex h-full w-full overflow-hidden">
      {isSidebarMobile && inboxOpen ? (
        <div className="flex h-full w-full flex-col">
          <SidebarHeader className="pb-0 pt-4">
            <div className="flex items-center gap-2 px-2">
              <button
                type="button"
                onClick={() => setInboxOpen(false)}
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-md p-1"
                aria-label="Back to sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <h2 className="text-sm font-medium">{t("nav.inbox")}</h2>
              <button
                type="button"
                onClick={() => setInboxOpen(false)}
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground ml-auto rounded-md p-1"
                aria-label="Close inbox"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <SidebarSeparator className="mx-0" />
          </SidebarHeader>
          <ScrollArea className="h-full">
            <InboxEmptyState />
          </ScrollArea>
        </div>
      ) : (
      <div className="flex h-full w-full flex-col md:w-(--app-sidebar-main-width) md:min-w-(--app-sidebar-main-width) group-data-[collapsible=icon]:w-(--sidebar-width-icon) group-data-[collapsible=icon]:min-w-(--sidebar-width-icon)">
        <SidebarHeader className="pb-0 pt-4">
          <SidebarMenu>
            <SidebarMenuItem>
              <Link to="/" aria-label={displayTitle}>
                <div className="flex items-center justify-center">
                  <h1
                    className="text-2xl font-serif font-semibold text-foreground cursor-pointer"
                    onClick={() => navigate("/")}
                  >
                    <span className="transition-[opacity,transform,margin] duration-200 ease-linear group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:hidden">
                      {displayTitle}
                    </span>
                    <span
                      aria-hidden="true"
                      className="hidden ml-0 transition-[opacity,transform,margin] duration-200 ease-linear group-data-[collapsible=icon]:inline group-data-[collapsible=icon]:opacity-100"
                    >
                      F
                    </span>
                  </h1>
                </div>
              </Link>
            </SidebarMenuItem>
          </SidebarMenu>
          <SidebarSeparator className="mx-0" />
        </SidebarHeader>
        <ScrollArea className="overflow-y-auto h-full">

        <SidebarContent className="gap-0">
          <SidebarGroup>
            <SidebarGroupContent>
              <NavMain
                isInboxOpen={inboxOpen}
                onInboxToggle={() => {
                  setOpen(true);
                  setInboxOpen((current) => !current);
                }}
              />
            </SidebarGroupContent>
          </SidebarGroup>
          <SidebarGroup>
            <SidebarGroupLabel>{t("sidebar.classes")}</SidebarGroupLabel>
            <SidebarGroupContent className="flex flex-col">
              <SidebarMenu>
                <Collapsible open={coursesOpen} onOpenChange={setCoursesOpen} className="group/collapsible">
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      tooltip={t("sidebar.courses.title")}
                      onClick={() => {
                        if (state === "collapsed") {
                          setOpen(true);
                          setCoursesOpen(true);
                          return;
                        }
                        setCoursesOpen((current) => !current);
                      }}
                    >
                      <BookOpen />
                      <span>{t("sidebar.courses.title")}</span>
                      <ChevronRight
                        className={`ml-auto transition-transform duration-200 ${coursesOpen ? "rotate-90" : ""}`}
                      />
                    </SidebarMenuButton>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {courses.slice(0, 3).map((course) => (
                          <SidebarMenuSubItem key={course.id}>
                            <SidebarMenuSubButton asChild>
                              <Link to={`/courses/${course.id}`}>
                                <span>{course.name}</span>
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                        {courses.length > 3 && (
                          <SidebarMenuSubItem>
                            <SidebarMenuSubButton
                              asChild
                              className="text-muted-foreground"
                            >
                              <Link
                                to="/courses"
                                className="flex items-center gap-2 text-muted-foreground"
                              >
                                <span>{t("sidebar.courses.seeAll")}</span>
                                <span className="text-muted-foreground">
                                  <ChevronRight className="h-4 w-4" />
                                </span>
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        )}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>

                <Collapsible open={assignmentsOpen} onOpenChange={setAssignmentsOpen} className="group/collapsible">
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      tooltip={t("sidebar.assignments.title")}
                      onClick={() => {
                        if (state === "collapsed") {
                          setOpen(true);
                          setAssignmentsOpen(true);
                          return;
                        }
                        setAssignmentsOpen((current) => !current);
                      }}
                    >
                      <FileText />
                      <span>{t("sidebar.assignments.title")}</span>
                      <ChevronRight
                        className={`ml-auto transition-transform duration-200 ${assignmentsOpen ? "rotate-90" : ""}`}
                      />
                    </SidebarMenuButton>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {(showAllAssignments
                          ? assignments
                          : assignments.slice(0, 3)
                        ).map((assignment) => (
                          <SidebarMenuSubItem key={assignment.id}>
                            <SidebarMenuSubButton asChild>
                              <Link
                                to={`/courses/${assignment.courseId}/assignments/${assignment.id}`}
                              >
                                <span>{assignment.title}</span>
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                        {assignments.length > 3 && !showAllAssignments && (
                          <SidebarMenuSubItem>
                            <SidebarMenuSubButton
                              className="text-muted-foreground"
                              onClick={() => setShowAllAssignments(true)}
                            >
                              <span>{t("sidebar.assignments.showMore")}</span>
                              <span className="text-muted-foreground">
                                <Plus className="h-4 w-4" />
                              </span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        )}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarGroup className="mt-auto">
            <SidebarGroupContent>
              <NavSecondary onSettingsClick={() => setSettingsOpen(true)} />
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        </ScrollArea>

        <SidebarFooter >
          <SidebarGroup className="p-0">
            <SidebarGroupContent className="flex flex-col gap-2">
              {isAuthenticated ? (
                <SidebarMenu>
                  <SidebarMenuItem>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuButton
                          size="lg"
                          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                        >
                          <UserAvatar
                            avatarSrc={null}
                            username={userName}
                            className="h-8 w-8 rounded-lg"
                          />
                          <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                            <span className="truncate font-medium">
                              {userName}
                            </span>
                            <span className="text-muted-foreground truncate text-xs">
                              {userEmail}
                            </span>
                          </div>
                          <ChevronsUpDown className="ml-auto size-4 group-data-[collapsible=icon]:hidden" />
                        </SidebarMenuButton>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
                        side={isMobile ? "bottom" : "right"}
                        align="end"
                        sideOffset={4}
                      >
                        <DropdownMenuLabel className="p-0 font-normal">
                          <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                            <UserAvatar
                              avatarSrc={null}
                              username={userName}
                              className="h-8 w-8 rounded-lg"
                            />
                            <div className="grid flex-1 text-left text-sm leading-tight">
                              <span className="truncate font-medium">
                                {userName}
                              </span>
                              <span className="text-muted-foreground truncate text-xs">
                                {userEmail}
                              </span>
                            </div>
                          </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onSelect={(event) => event.preventDefault()}
                          className="flex items-center"
                        >
                          <span>{t("menu.account")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuSub>
                          <DropdownMenuSubTrigger className="flex items-center">
                            <span>{t("menu.theme")}</span>
                          </DropdownMenuSubTrigger>
                          <DropdownMenuSubContent>
                            <DropdownMenuRadioGroup
                              value={effectiveTheme}
                              onValueChange={(value) =>
                                setThemePreference(value as "light" | "dark" | "system")
                              }
                            >
                              <DropdownMenuRadioItem value="light">
                                {t("theme.light")}
                              </DropdownMenuRadioItem>
                              <DropdownMenuRadioItem value="dark">
                                {t("theme.dark")}
                              </DropdownMenuRadioItem>
                              <DropdownMenuRadioItem value="system">
                                {t("theme.system")}
                              </DropdownMenuRadioItem>
                            </DropdownMenuRadioGroup>
                          </DropdownMenuSubContent>
                        </DropdownMenuSub>
                        <DropdownMenuSub>
                          <DropdownMenuSubTrigger className="flex items-center">
                            <span>{t("menu.language")}</span>
                          </DropdownMenuSubTrigger>
                          <DropdownMenuSubContent>
                            <DropdownMenuRadioGroup
                              value={currentLanguage.code}
                              onValueChange={(value) =>
                                setLanguagePreference(value as "en" | "es")
                              }
                            >
                              {languages.map((lang) => (
                                <DropdownMenuRadioItem
                                  key={lang.code}
                                  value={lang.code}
                                >
                                  {lang.name}
                                </DropdownMenuRadioItem>
                              ))}
                            </DropdownMenuRadioGroup>
                          </DropdownMenuSubContent>
                        </DropdownMenuSub>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => {
                            logout();
                            navigate("/login");
                          }}
                        >
                          <LogOut className="mr-2 h-4 w-4" />
                          <span>{t("menu.logout")}</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                </SidebarMenu>
              ) : (
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton asChild tooltip={t("header.login")}>
                      <Link to="/login">
                        <User />
                        <span>{t("header.login")}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              )}
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarFooter>
      </div>
      )}
      {inboxOpen && (
        <aside className="hidden border-l bg-sidebar md:flex md:flex-col">
          <div className="border-b p-4">
            <div className="flex items-center">
              <h2 className="font-medium">{t("nav.inbox")}</h2>
              <Button
                onClick={() => setInboxOpen(false)}
                className="ml-auto"
                size="icon"
                variant="ghost"
                aria-label="Close inbox"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <ScrollArea className="h-full">
            <InboxEmptyState />
          </ScrollArea>
        </aside>
      )}
      </div>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} isMobile={isMobile} />
    </Sidebar>
  );
}
