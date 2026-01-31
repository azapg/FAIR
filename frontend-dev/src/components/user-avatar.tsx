import React from "react";
import { Avatar, AvatarImage, AvatarFallback } from "facehash";

const COLORS = ["#7c67f5", "#e9c46a", "#f56773", "#e0f567", "#67f5e2", "#f5a667"];

export type UserAvatarProps = {
  /**
   * URL of the avatar image. If not provided or image fails to load,
   * the initials fallback will be rendered.
   */
  avatarSrc?: string | null;
  /**
   * Display name used for alt text and generating initials.
   */
  username?: string | null;
  /**
   * Optional fallback string used when username is not available
   * to generate a single-character fallback.
   */
  fallback?: string;
  /**
   * Size of the rendered avatar. Accepts either a numeric pixel value
   * or a predefined size token.
   */
  size?: number | "sm" | "md" | "lg" | "xl";
  /**
   * Tailwind (or other) classes applied to the outer Avatar element.
   */
  className?: string;
  /**
   * Whether the avatar should have rounded-full (circle) or rounded-lg.
   * Defaults to rounded-lg to match existing app visuals.
   */
  circular?: boolean;
  /**
   * Optional color palette passed to facehash for the generated fallback.
   */
  facehashColors?: string[];
  /**
   * If true, the username text will be rendered to the right of the avatar.
   * This component focuses on avatar rendering; when showing username the
   * consumer should handle layout concerns as needed.
   */
  showName?: boolean;
  /**
   * Optional text class for the username when `showName` is true.
   */
  nameClassName?: string;
};

/**
 * Reusable UserAvatar component.
 *
 * - Uses the project's `facehash` Avatar primitives (`AvatarImage` + `AvatarFallback`)
 * - Accepts `avatarSrc` and `username` as the primary inputs
 * - Allows size and shape customization and passes a color palette into facehash
 */
export const UserAvatar: React.FC<UserAvatarProps> = ({
  avatarSrc,
  username,
  fallback = "User",
  size = "md",
  className = "",
  circular = false,
  facehashColors = COLORS,
  showName = false,
  nameClassName = "truncate font-medium",
}) => {
  const sizeClass =
    typeof size === "string"
      ? size === "sm"
        ? "h-6 w-6 text-xs"
        : size === "lg"
        ? "h-10 w-10 text-sm"
        : size === "xl"
        ? "h-12 w-12 text-base"
        : "h-8 w-8 text-xs" // md
      : undefined;

  const inlineStyle =
    typeof size === "number"
      ? { width: size, height: size, minWidth: size, minHeight: size }
      : undefined;

  const roundedClass = circular ? "rounded-full" : "rounded-lg";

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <Avatar
        className={`${roundedClass} ${sizeClass ?? ""} flex-shrink-0`}
        style={inlineStyle}
        aria-hidden={false}
      >
        <AvatarImage src={avatarSrc} alt={username ?? fallback} />
        <AvatarFallback
          className={`${roundedClass} ${sizeClass ? "text-xs" : ""}`}
          name={username ?? fallback}
          facehashProps={{ colors: facehashColors }}
        >
        </AvatarFallback>
      </Avatar>

      {showName && (
        <span className={nameClassName} title={username ?? fallback}>
          {username ?? fallback}
        </span>
      )}
    </div>
  );
};

export default UserAvatar;
