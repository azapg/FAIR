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
  SidebarMenuBadge,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import { useEffect, useId, useState } from "react";
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
  Puzzle,
  ListTodo,
  LayoutDashboard,
} from "lucide-react";
import { Menu02Icon } from "hugeicons-react";
import {
  Collapsible,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/auth-context";
import { useIsMobile } from "@/hooks/use-mobile";
import { hasStaffCourseMembership, useCourses } from "@/hooks/use-courses";
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
import {
  type LanguageCode,
  type ThemeMode,
  usePreferenceSettings,
} from "@/hooks/use-preference-settings";
import { IfSetting } from "@/components/if-setting";
import { AppSearch } from "@/components/app-search";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Button } from "@/components/ui/button";
import { Can } from "@/components/can";
import { CourseIcon } from "@/app/courses/course-icons";
import {
  useNotifications,
  useReadAllNotifications,
  useReadNotification,
} from "@/hooks/use-communication";

const languages = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
] satisfies { code: LanguageCode; name: string }[];

function SidebarPreferencesMenu({
  effectiveLanguage,
  effectiveTheme,
  isMobile,
  setLanguagePreference,
  setThemePreference,
}: {
  effectiveLanguage: LanguageCode;
  effectiveTheme: ThemeMode;
  isMobile: boolean;
  setLanguagePreference: (language: LanguageCode) => void;
  setThemePreference: (theme: ThemeMode) => void;
}) {
  const { t } = useTranslation();
  const [mobileSection, setMobileSection] = useState<
    "theme" | "language" | null
  >(null);
  const themeContentId = useId();
  const languageContentId = useId();

  const themeOptions = (
    <DropdownMenuRadioGroup
      value={effectiveTheme}
      onValueChange={(value) => setThemePreference(value as ThemeMode)}
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
  );
  const languageOptions = (
    <DropdownMenuRadioGroup
      value={effectiveLanguage}
      onValueChange={(value) => setLanguagePreference(value as LanguageCode)}
    >
      {languages.map((language) => (
        <DropdownMenuRadioItem key={language.code} value={language.code}>
          {language.name}
        </DropdownMenuRadioItem>
      ))}
    </DropdownMenuRadioGroup>
  );

  if (!isMobile) {
    return (
      <>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center">
            <span>{t("menu.theme")}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>{themeOptions}</DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center">
            <span>{t("menu.language")}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>{languageOptions}</DropdownMenuSubContent>
        </DropdownMenuSub>
      </>
    );
  }

  return (
    <>
      <Collapsible open={mobileSection === "theme"}>
        <DropdownMenuItem
          aria-controls={themeContentId}
          aria-expanded={mobileSection === "theme"}
          className="flex items-center"
          onSelect={(event) => {
            event.preventDefault();
            setMobileSection((section) =>
              section === "theme" ? null : "theme",
            );
          }}
        >
          <span>{t("menu.theme")}</span>
          <ChevronRight
            className={`ml-auto transition-transform duration-200 ${mobileSection === "theme" ? "rotate-90" : ""}`}
          />
        </DropdownMenuItem>
        <CollapsibleContent
          id={themeContentId}
          className="border-border/60 mx-1 mb-1 border-l pl-1"
        >
          {themeOptions}
        </CollapsibleContent>
      </Collapsible>
      <Collapsible open={mobileSection === "language"}>
        <DropdownMenuItem
          aria-controls={languageContentId}
          aria-expanded={mobileSection === "language"}
          className="flex items-center"
          onSelect={(event) => {
            event.preventDefault();
            setMobileSection((section) =>
              section === "language" ? null : "language",
            );
          }}
        >
          <span>{t("menu.language")}</span>
          <ChevronRight
            className={`ml-auto transition-transform duration-200 ${mobileSection === "language" ? "rotate-90" : ""}`}
          />
        </DropdownMenuItem>
        <CollapsibleContent
          id={languageContentId}
          className="border-border/60 mx-1 mb-1 border-l pl-1"
        >
          {languageOptions}
        </CollapsibleContent>
      </Collapsible>
    </>
  );
}

const courseIconBackgrounds = [
  "from-rose-400 to-orange-500",
  "from-sky-400 to-indigo-500",
  "from-emerald-400 to-teal-500",
  "from-violet-400 to-fuchsia-500",
  "from-amber-400 to-rose-500",
  "from-cyan-400 to-blue-500",
  "from-lime-400 to-emerald-500",
  "from-pink-400 to-purple-500",
] as const;

function getCourseIconBackground(courseId: string) {
  const hash = Array.from(courseId).reduce(
    (value, character) => (value * 31 + character.charCodeAt(0)) >>> 0,
    0,
  );

  return courseIconBackgrounds[hash % courseIconBackgrounds.length];
}

function NotificationsInbox() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: notifications = [], isLoading } = useNotifications();
  const readNotification = useReadNotification();
  const readAll = useReadAllNotifications();

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Loading notifications…</div>;

  if (notifications.length > 0) {
    return (
      <div className="p-3">
        <div className="mb-2 flex justify-end">
          <Button size="sm" variant="ghost" onClick={() => readAll.mutate()}>Mark all read</Button>
        </div>
        <div className="space-y-2">
          {notifications.map((notification) => (
            <button
              type="button"
              key={notification.id}
              className={`w-full rounded-md border p-3 text-left ${notification.readAt ? 'opacity-70' : 'bg-sidebar-accent'}`}
              onClick={() => {
                if (!notification.readAt) readNotification.mutate(notification.id);
                if (notification.link) navigate(notification.link);
              }}
            >
              <div className="text-sm font-medium">{notification.title}</div>
              {notification.body && <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{notification.body}</div>}
              <div className="mt-2 text-xs text-muted-foreground">{new Date(notification.createdAt).toLocaleString()}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

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
      </EmptyContent>
    </Empty>
  );
}

function NavMain({
  isInboxOpen,
  onInboxToggle,
  isSearchOpen,
  onSearchClick,
  unreadCount,
  showStudentDashboard,
}: {
  isInboxOpen: boolean;
  onInboxToggle: () => void;
  isSearchOpen: boolean;
  onSearchClick: () => void;
  unreadCount: number;
  showStudentDashboard: boolean;
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

      {showStudentDashboard && (
        <SidebarMenuItem>
          <SidebarMenuButton asChild tooltip="Dashboard">
            <Link to="/dashboard">
              <LayoutDashboard />
              <span>Dashboard</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      )}

      {/*search*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="To-do">
          <Link to="/todo">
            <ListTodo />
            <span>To-do</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>

      <SidebarMenuItem>
        <SidebarMenuButton
          tooltip={t("nav.search")}
          onClick={onSearchClick}
          isActive={isSearchOpen}
        >
          <SearchIcon />
          <span>{t("nav.search")}</span>
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
        {unreadCount > 0 && (
          <SidebarMenuBadge className="rounded-full bg-primary px-1.5 text-xs !text-primary-foreground">
            {unreadCount}
          </SidebarMenuBadge>
        )}
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
      <Can I="admin">
        <SidebarMenuItem>
          <SidebarMenuButton asChild tooltip={t("nav.extensions")}>
            <Link to="/extensions">
              <Puzzle />
              <span>{t("nav.extensions")}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </Can>
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
  const { t } = useTranslation();
  const { user: authUser, isAuthenticated, logout } = useAuth();
  const {
    effectiveLanguage,
    effectiveTheme,
    setLanguagePreference,
    setThemePreference,
  } = usePreferenceSettings();
  const isMobile = useIsMobile();
  const { data: courses = [], isLoading: coursesLoading } = useCourses();
  const { data: eligibilityCourses = [], isLoading: eligibilityCoursesLoading } =
    useCourses({ include_archived: true }, Boolean(authUser));
  const { data: assignments = [] } = useAllAssignments(isAuthenticated);
  const { data: notifications = [] } = useNotifications(isAuthenticated);
  const unreadCount = notifications.filter((notification) => !notification.readAt).length;
  const {
    setOpen,
    state,
    isMobile: isSidebarMobile,
    openMobile,
    width: sidebarWidth = "20rem",
  } = useSidebar();
  const [showAllAssignments, setShowAllAssignments] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [coursesOpen, setCoursesOpen] = useState(true);
  const [assignmentsOpen, setAssignmentsOpen] = useState(false);
  const coursesContentId = useId();
  const assignmentsContentId = useId();
  const showStudentDashboard = !coursesLoading
    && !eligibilityCoursesLoading
    && authUser?.role === 'user'
    && !hasStaffCourseMembership(eligibilityCourses);

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

  const sidebarStyle = {
    ...(style ?? {}),
    ["--sidebar-width" as string]:
      !isSidebarMobile && inboxOpen
        ? `calc(${sidebarWidth} + 20rem)`
        : isSidebarMobile
          ? "20rem"
          : sidebarWidth,
    ["--app-sidebar-main-width" as string]: isSidebarMobile
      ? sidebarWidth
      : `calc(${sidebarWidth} - 1rem)`,
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
            <NotificationsInbox />
          </ScrollArea>
        </div>
      ) : (
      <div className="flex h-full w-full flex-col md:w-(--app-sidebar-main-width) md:min-w-(--app-sidebar-main-width) group-data-[collapsible=icon]:w-(--sidebar-width-icon) group-data-[collapsible=icon]:min-w-(--sidebar-width-icon)">
        <SidebarHeader className="pb-0 pt-4">
          <SidebarMenu>
            <SidebarMenuItem>
              <Link
                to="/"
                aria-label={state === "collapsed" ? "Open sidebar" : displayTitle}
                title={state === "collapsed" ? "Open sidebar" : displayTitle}
                className="group/brand"
                onClick={(event) => {
                  if (state === "collapsed") {
                    event.preventDefault();
                    setOpen(true);
                  }
                }}
              >
                <div className="flex items-center justify-center">
                  <h1 className="text-2xl font-serif font-semibold text-foreground cursor-pointer">
                    <span className="transition-[opacity,transform,margin] duration-200 ease-linear group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:hidden">
                      {displayTitle}
                    </span>
                    <span
                      aria-hidden="true"
                      className="hidden ml-0 transition-[opacity,transform,margin] duration-200 ease-linear group-data-[collapsible=icon]:inline group-data-[collapsible=icon]:opacity-100"
                    >
                      <span className="group-hover/brand:hidden">F</span>
                      <Menu02Icon className="hidden size-5 group-hover/brand:inline" />
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
                isSearchOpen={searchOpen}
                onSearchClick={() => setSearchOpen(true)}
                onInboxToggle={() => {
                  setOpen(true);
                  setInboxOpen((current) => !current);
                }}
                unreadCount={unreadCount}
                showStudentDashboard={showStudentDashboard}
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
                      aria-expanded={coursesOpen}
                      aria-controls={coursesContentId}
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
                    <CollapsibleContent id={coursesContentId}>
                      <SidebarMenuSub>
                        {courses.slice(0, 3).map((course) => (
                          <SidebarMenuSubItem key={course.id}>
                            <SidebarMenuSubButton asChild>
                              <Link
                                to={`/courses/${course.id}`}
                                className="group/course h-8 gap-2.5"
                              >
                                <span
                                  className={`grid size-6 shrink-0 place-items-center rounded-full border border-white/15 bg-gradient-to-br text-white shadow-[var(--shadow-button)] transition-transform duration-150 ease-out group-hover/course:-translate-y-px group-active/course:translate-y-0 group-active/course:scale-[0.96] ${getCourseIconBackground(course.id)}`}
                                >
                                  <CourseIcon iconKey={course.iconKey} size={14} />
                                </span>
                                <span className="truncate">{course.name}</span>
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
                      aria-expanded={assignmentsOpen}
                      aria-controls={assignmentsContentId}
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
                    <CollapsibleContent id={assignmentsContentId}>
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
                        side="top"
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
                        <SidebarPreferencesMenu
                          effectiveLanguage={effectiveLanguage}
                          effectiveTheme={effectiveTheme}
                          isMobile={isSidebarMobile}
                          setLanguagePreference={setLanguagePreference}
                          setThemePreference={setThemePreference}
                        />
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
            <NotificationsInbox />
          </ScrollArea>
        </aside>
      )}
      </div>
      <AppSearch
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} isMobile={isMobile} />
      <SidebarRail />
    </Sidebar>
  );
}
