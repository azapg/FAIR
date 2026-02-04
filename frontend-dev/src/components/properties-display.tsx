import * as React from "react";
import { cn } from "@/lib/utils";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

type PropertiesDisplayProps = React.HTMLAttributes<HTMLDivElement> & {
  scroll?: boolean;
};

function PropertiesDisplay({ className, scroll, ...props }: PropertiesDisplayProps) {
  const content = (
    <div
      className={cn("grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-3", className)}
      {...props}
    />
  );

  if (!scroll) {
    return content;
  }

  return (
    <ScrollArea className="w-full h-auto">
      {content}
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  );
}

type PropertyProps = React.HTMLAttributes<HTMLDivElement>;

function Property({ className, ...props }: PropertyProps) {
  return (
    <div
      className={cn("contents", className)}
      {...props}
    />
  );
}

type PropertyLabelProps = React.HTMLAttributes<HTMLDivElement>;

function PropertyLabel({ className, ...props }: PropertyLabelProps) {
  return (
    <div
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

type PropertyValueProps = React.HTMLAttributes<HTMLDivElement>;

function PropertyValue({ className, ...props }: PropertyValueProps) {
  return <div className={cn(className)} {...props} />;
}

export {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
};