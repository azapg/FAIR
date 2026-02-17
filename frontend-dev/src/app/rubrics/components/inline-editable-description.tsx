import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";

export function InlineEditableDescription({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  const [isEditing, setIsEditing] = useState(false);

  if (!isEditing) {
    return (
      <button
        type="button"
        className="w-full rounded-md p-2 text-left hover:bg-muted/40 transition-colors"
        onClick={() => setIsEditing(true)}
      >
        <p
          className={`text-sm whitespace-pre-wrap break-words line-clamp-3 ${
            value ? "text-foreground" : "text-muted-foreground italic"
          }`}
        >
          {value || placeholder}
        </p>
      </button>
    );
  }

  return (
    <Textarea
      autoFocus
      rows={4}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onBlur={() => setIsEditing(false)}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          setIsEditing(false);
        }
      }}
      className="min-h-24 text-sm border-border/50 focus-visible:ring-1 focus-visible:ring-ring/40"
      placeholder={placeholder}
    />
  );
}
