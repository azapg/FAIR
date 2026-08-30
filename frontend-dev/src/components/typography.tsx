import { cn } from "@/lib/utils";
import React from "react";

interface TypographyProps {
  children: React.ReactNode;
  className?: string;
}

// Heading Components
export function H1({ children, className }: TypographyProps) {
  return (
    <h1 className={cn("text-[1.625rem] leading-[1.15] font-semibold tracking-[-0.025em] text-foreground", className)}>
      {children}
    </h1>
  );
}

export function H2({ children, className }: TypographyProps) {
  return (
    <h2 className={cn("text-xl leading-6 font-semibold tracking-[-0.02em] text-foreground", className)}>
      {children}
    </h2>
  );
}

export function H3({ children, className }: TypographyProps) {
  return (
    <h3 className={cn("text-base leading-5 font-semibold tracking-[-0.012em] text-foreground", className)}>
      {children}
    </h3>
  );
}

export function H4({ children, className }: TypographyProps) {
  return (
    <h4 className={cn("text-sm leading-5 font-semibold text-foreground", className)}>
      {children}
    </h4>
  );
}

export function H5({ children, className }: TypographyProps) {
  return (
    <h5 className={cn("text-[0.8125rem] leading-4 font-semibold text-foreground", className)}>
      {children}
    </h5>
  );
}

// Body Text Components
export function Lead({ children, className }: TypographyProps) {
  return (
    <p className={cn("text-[0.9375rem] leading-6 text-foreground", className)}>
      {children}
    </p>
  );
}

export function Body({ children, className }: TypographyProps) {
  return (
    <p className={cn("text-sm leading-5 text-foreground", className)}>
      {children}
    </p>
  );
}

export function BodyMuted({ children, className }: TypographyProps) {
  return (
    <p className={cn("text-[0.8125rem] leading-[1.45] text-muted-foreground", className)}>
      {children}
    </p>
  );
}

export function Small({ children, className }: TypographyProps) {
  return (
    <p className={cn("text-[0.8125rem] leading-4 text-muted-foreground", className)}>
      {children}
    </p>
  );
}

// List Component
export function List({ children, className }: TypographyProps) {
  return (
    <ul className={cn("text-sm leading-5 text-foreground space-y-2", className)}>
      {children}
    </ul>
  );
}

// Quote Component
export function Quote({ children, className }: TypographyProps) {
  return (
    <blockquote className={cn("text-sm leading-5 italic text-muted-foreground border-l-2 border-primary pl-4", className)}>
      {children}
    </blockquote>
  );
}

// Code Component
export function Code({ children, className }: TypographyProps) {
  return (
    <code className={cn("font-mono text-sm bg-muted px-2 py-1 rounded", className)}>
      {children}
    </code>
  );
}
