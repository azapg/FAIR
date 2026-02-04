import * as React from "react";
import { cn } from "@/lib/utils";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

type PropertiesDisplayProps = React.HTMLAttributes<HTMLDivElement> & {
  scroll?: boolean;
  valueAlign?: "left" | "center" | "right";
  gapX?: number;
};

function PropertiesDisplay({
  className,
  scroll,
  valueAlign = "left",
  gapX,
  ...props
}: PropertiesDisplayProps) {
  const styles = {
    "--value-align": valueAlign,
    ...(gapX !== undefined && { columnGap: `${gapX}rem` }),
    ...props.style,
  } as React.CSSProperties;

  const content = (
    <div
      className={cn(
        "grid grid-cols-[max-content_1fr] items-center gap-y-3",
        gapX === undefined && "gap-x-4",
        className,
      )}
      style={styles}
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

function PropertyValue({ className, style, ...props }: PropertyValueProps) {
  const componentStyle: React.CSSProperties = {
    textAlign: "var(--value-align, left)" as "left" | "center" | "right",
    ...style,
  };
  return <div className={cn(className)} style={componentStyle} {...props} />;
}

export {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
};