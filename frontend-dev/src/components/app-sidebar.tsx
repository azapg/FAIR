import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import type { ComponentProps } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookOpen, Home, LogOut, User } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/components/theme-provider";
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
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <Link to="/">
              <div className="flex justify-center items-center">
                <h1
                  className="text-2xl font-serif font-semibold text-foreground cursor-pointer"
                  onClick={() => navigate("/")}
                >
                  {displayTitle}
                </h1>
              </div>{" "}
            </Link>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent className="flex flex-col gap-2">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Home">
                  <Link to="/">
                    <Home />
                    <span>Home</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Courses">
                  <Link to="/courses">
                    <BookOpen />
                    <span>Courses</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarGroup>
          <SidebarGroupContent className="flex flex-col gap-2">
            {isAuthenticated ? (
              <SidebarMenu>
                <SidebarMenuItem>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <SidebarMenuButton
                        size="lg"
                        className="w-full data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                      >
                        <Avatar className="h-8 w-8 rounded-lg">
                          <AvatarImage src={authUser?.avatar} alt={userName} />
                          <AvatarFallback className="rounded-lg text-xs">
                            {initials}
                          </AvatarFallback>
                        </Avatar>
                        <div className="grid flex-1 text-left text-sm leading-tight ml-2">
                          <span className="truncate font-medium">{userName}</span>
                          <span className="text-muted-foreground truncate text-xs">
                            {userEmail}
                          </span>
                        </div>
                      </SidebarMenuButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
                      side="right"
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
