import React from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Settings, User, LogOut, HelpCircle } from "lucide-react";
import {ThemeToggle} from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import {useNavigate} from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "@/components/language-switcher";

interface HeaderProps {
  /**
   * User information for the avatar and dropdown
   */
  user?: {
    name?: string;
    email?: string;
    avatar?: string;
    initials?: string;
  };
  /**
   * Custom title to display instead of "Fair Platform"
   * TODO: Maybe allowing an image or logo here would be useful in the future
   * @default "Fair Platform"
   */
  title?: string;
  /**
   * Additional content to render in the center of the header
   */
  centerContent?: React.ReactNode;
  /**
   * Additional content to render on the right side before the avatar
   */
  rightContent?: React.ReactNode;
  /**
   * Custom dropdown menu items
   */
  dropdownItems?: Array<{
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
    separator?: boolean;
  }>;
  /**
   * Callback when user clicks settings_schema
   */
  onSettingsClick?: () => void;
  /**
   * Callback when user clicks profile
   */
  onProfileClick?: () => void;
  /**
   * Callback when user clicks logout
   */
  onLogoutClick?: () => void;
  /**
   * Custom CSS classes for the header container
   */
  className?: string;
}

function getInitials(name?: string, fallback?: string) {
  if (name && name.trim().length > 0) {
    const parts = name.trim().split(/\s+/).filter(Boolean).slice(0, 2);
    const initials = parts.map(p => p[0]?.toUpperCase()).join("");
    if (initials) return initials;
  }
  return (fallback?.[0] || "U").toUpperCase();
}

function Header({
  title,
  centerContent,
  rightContent,
  dropdownItems,
  onSettingsClick,
  onProfileClick,
  onLogoutClick,
  className = "",
}: HeaderProps) {
  const navigate = useNavigate();
  const { user: authUser, isAuthenticated, logout } = useAuth();
  const { t } = useTranslation();

  const displayTitle = title || t("header.title");

  const activeUser = isAuthenticated ? {
    name: authUser?.name,
    email: authUser?.email,
    avatar: undefined as string | undefined,
  } : undefined;

  const computedInitials = getInitials(activeUser?.name, activeUser?.email);

  const defaultDropdownItems = [
    {
      label: t("header.profile"),
      icon: <User className="h-4 w-4" />,
      onClick: onProfileClick || (() => console.log("Profile clicked")),
    },
    {
      label: t("header.settings"),
      icon: <Settings className="h-4 w-4" />,
      onClick: onSettingsClick || (() => console.log("Settings clicked")),
    },
    {
      label: t("header.help"),
      icon: <HelpCircle className="h-4 w-4" />,
      onClick: () => console.log("Help clicked"),
    },
    {
      label: t("header.logout"),
      icon: <LogOut className="h-4 w-4" />,
      onClick: onLogoutClick || (() => {
        logout()
        navigate("/login")
      }),
      separator: true,
    },
  ];

  const menuItems = dropdownItems || defaultDropdownItems;

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-16 px-6 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 ${className}`}
    >
      {/* Left section - Platform title */}
      <div className="flex items-center">
        <h1 className="text-xl font-serif font-semibold text-foreground cursor-pointer" onClick={() => navigate("/")}>{displayTitle}</h1>
      </div>

      {/* Center section - Extensible content */}
      {centerContent && (
        <div className="flex-1 flex items-center justify-center px-6">
          {centerContent}
        </div>
      )}

      {/* Right section - Additional content and auth */}
      <div className="flex items-center gap-3">
        {rightContent}
        <LanguageSwitcher />
        <ThemeToggle />
        {!isAuthenticated ? (
          <Button onClick={() => navigate("/login")}>
            {t("header.login")}
          </Button>
        ) : (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={activeUser?.avatar} alt={activeUser?.name || "User"} />
                  <AvatarFallback className="text-sm">
                    {computedInitials}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {activeUser?.name || "User"}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {activeUser?.email || "user@example.com"}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {menuItems.map((item, index) => (
                <React.Fragment key={index}>
                  {item.separator && <DropdownMenuSeparator />}
                  <DropdownMenuItem onClick={item.onClick} className="cursor-pointer">
                    {item.icon && <span className="mr-2">{item.icon}</span>}
                    {item.label}
                  </DropdownMenuItem>
                </React.Fragment>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}

export default Header;