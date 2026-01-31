import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css'; // Import KaTeX CSS for proper styling
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  children: any;
  className?: string;
  compact?: boolean;
}

export function MarkdownRenderer({ children, className, compact }: MarkdownRendererProps) {
  return (
    <div className={cn("markdown-content", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Custom styling for markdown elements to match the design system
          h1: ({node, ...props}) => <h1 className={cn("text-2xl", !compact && "mb-4")} {...props} />,
          p: ({node, ...props}) => <p className={cn("leading-relaxed", !compact && "mb-4")} {...props} />,
          h2: ({node, ...props}) => <h2 className={cn("text-xl", !compact && "mb-3")} {...props} />,
          h3: ({node, ...props}) => <h3 className={cn("text-lg", !compact && "mb-2")} {...props} />,
          h4: ({node, ...props}) => <h4 className={cn("text-base", !compact && "mb-2")} {...props} />,
          h5: ({node, ...props}) => <h5 className={cn("text-sm", !compact && "mb-2")} {...props} />,
          h6: ({node, ...props}) => <h6 className={cn("text-sm", !compact && "mb-2")} {...props} />,
          ul: ({node, ...props}) => <ul className={cn("list-disc list-inside space-y-1", !compact && "mb-4")} {...props} />,
          ol: ({node, ...props}) => <ol className={cn("list-decimal list-inside space-y-1", !compact && "mb-4")} {...props} />,
          li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
          strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
          em: ({node, ...props}) => <em className="italic" {...props} />,
          code: ({node, ...props}) => <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...props} />,
          pre: ({node, ...props}) => <pre className={cn("bg-muted p-4 rounded-lg overflow-x-auto", !compact && "mb-4")} {...props} />,
          blockquote: ({node, ...props}) => <blockquote className={cn("border-l-4 border-primary pl-4 italic text-muted-foreground", !compact && "mb-4")} {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}