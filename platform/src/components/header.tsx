"use client";

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
   * Callback when user clicks settings
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

export function Header({
  user = {
    name: "User",
    email: "user@example.com",
    initials: "U",
  },
  title = "The Fair Platform",
  centerContent,
  rightContent,
  dropdownItems,
  onSettingsClick,
  onProfileClick,
  onLogoutClick,
  className = "",
}: HeaderProps) {
  const defaultDropdownItems = [
    {
      label: "Profile",
      icon: <User className="h-4 w-4" />,
      onClick: onProfileClick || (() => console.log("Profile clicked")),
    },
    {
      label: "Settings",
      icon: <Settings className="h-4 w-4" />,
      onClick: onSettingsClick || (() => console.log("Settings clicked")),
    },
    {
      label: "Help",
      icon: <HelpCircle className="h-4 w-4" />,
      onClick: () => console.log("Help clicked"),
    },
    {
      label: "Logout",
      icon: <LogOut className="h-4 w-4" />,
      onClick: onLogoutClick || (() => console.log("Logout clicked")),
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
        <h1 className="text-xl font-serif font-semibold text-foreground">{title}</h1>
      </div>

      {/* Center section - Extensible content */}
      {centerContent && (
        <div className="flex-1 flex items-center justify-center px-6">
          {centerContent}
        </div>
      )}

      {/* Right section - Additional content and avatar */}
      <div className="flex items-center gap-4">
        {rightContent}
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user.avatar} alt={user.name || "User"} />
                <AvatarFallback className="text-sm">
                  {user.initials || user.name?.charAt(0).toUpperCase() || "U"}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {user.name || "User"}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user.email || "user@example.com"}
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
      </div>
    </header>
  );
}

export default Header;
