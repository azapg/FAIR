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
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import type { ComponentProps } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookOpen, ChevronRight, ChevronsUpDown, FileText, LogOut, User, Home, SearchIcon, InboxIcon, SettingsIcon, MessageCircleQuestionMarkIcon } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/components/theme-provider";
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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

function getInitials(name?: string, fallback?: string) {
  if (name && name.trim().length > 0) {
    const parts = name.trim().split(/\s+/).filter(Boolean).slice(0, 2);
    const initials = parts.map((p) => p[0]?.toUpperCase()).join("");
    if (initials) return initials;
  }
  return (fallback?.[0] || "U").toUpperCase();
}

const languages = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
];

function NavMain() {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Home">
          <Link to="/">
            <Home />
            <span>Home</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>

      {/*search*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Search">
          <Link to="/search">
            <SearchIcon />
            <span>Search</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>

      {/*inbox*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Inbox">
          <Link to="/inbox">
            <InboxIcon />
            <span>Inbox</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

function NavSecondary() {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Settings">
          <Link to="/settings">
            <SettingsIcon />
            <span>Settings</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
      {/*Help*/}
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip="Help">
          <Link to="/help">
            <MessageCircleQuestionMarkIcon />
            <span>Help</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
    
  )
}

export function AppSidebar({
  side = "left",
  className,
  ...props
}: ComponentProps<typeof Sidebar> & {
  side?: "left" | "right";
}) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { user: authUser, isAuthenticated, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const isMobile = useIsMobile();
  const { data: courses = [] } = useCourses();
  const { data: assignments = [] } = useAllAssignments(isAuthenticated);

  const displayTitle = t("header.title");
  const userName = authUser?.name || t("header.profile");
  const userEmail = authUser?.email || "user@example.com";
  const initials = getInitials(authUser?.name, authUser?.email);
  const currentLanguage =
    languages.find((lang) =>
      i18n.language?.toLowerCase().startsWith(lang.code)
    ) ?? languages[0];

  return (
    <Sidebar side={side} collapsible="icon" className={className} {...props}>
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
      <SidebarContent className="gap-0">
        <SidebarGroup>
          <SidebarGroupContent>
            <NavMain />
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Your classes</SidebarGroupLabel>
          <SidebarGroupContent className="flex flex-col">
            <SidebarMenu>
              <Collapsible defaultOpen className="group/collapsible">
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton tooltip="Courses">
                      <BookOpen />
                      <span>Courses</span>
                      <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      {courses.map((course) => (
                        <SidebarMenuSubItem key={course.id}>
                          <SidebarMenuSubButton asChild>
                            <Link to={`/courses/${course.id}`}>
                              <span>{course.name}</span>
                            </Link>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </Collapsible>

              <Collapsible className="group/collapsible">
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton tooltip="Assignments">
                      <FileText />
                      <span>Assignments</span>
                      <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      {assignments.map((assignment) => (
                        <SidebarMenuSubItem key={assignment.id}>
                          <SidebarMenuSubButton asChild>
                            <Link to={`/courses/${assignment.courseId}/assignments/${assignment.id}`}>
                              <span>{assignment.title}</span>
                            </Link>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </Collapsible>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <NavSecondary />
          </SidebarGroupContent>
        </SidebarGroup>

      </SidebarContent>
      <SidebarFooter>
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
                        <Avatar className="h-8 w-8 rounded-lg">
                          <AvatarImage src={authUser?.avatar} alt={userName} />
                          <AvatarFallback className="rounded-lg text-xs">
                            {initials}
                          </AvatarFallback>
                        </Avatar>
                        <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                          <span className="truncate font-medium">{userName}</span>
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
                          <Avatar className="h-8 w-8 rounded-lg">
                            <AvatarImage src={authUser?.avatar} alt={userName} />
                            <AvatarFallback className="rounded-lg text-xs">
                              {initials}
                            </AvatarFallback>
                          </Avatar>
                          <div className="grid flex-1 text-left text-sm leading-tight">
                            <span className="truncate font-medium">{userName}</span>
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
                        <span>Account</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger className="flex items-center">
                          <span>Theme</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          <DropdownMenuRadioGroup
                            value={theme}
                            onValueChange={(value) =>
                              setTheme(value as "light" | "dark" | "system")
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
                          <span>Language</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          <DropdownMenuRadioGroup
                            value={currentLanguage.code}
                            onValueChange={(value) => i18n.changeLanguage(value)}
                          >
                            {languages.map((lang) => (
                              <DropdownMenuRadioItem key={lang.code} value={lang.code}>
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
                        <span>Log out</span>
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
      <SidebarRail />
    </Sidebar>
  );
}
