import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css'; // Import KaTeX CSS for proper styling
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  children: string;
  className?: string;
}

export function MarkdownRenderer({ children, className }: MarkdownRendererProps) {
  return (
    <div className={cn("markdown-content", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Custom styling for markdown elements to match the design system
          h1: ({node, ...props}) => <h1 className="text-2xl mb-4" {...props} />,
          p: ({node, ...props}) => <p className="mb-4 leading-relaxed" {...props} />,
          h2: ({node, ...props}) => <h2 className="text-xl mb-3" {...props} />,
          h3: ({node, ...props}) => <h3 className="text-lg mb-2" {...props} />,
          h4: ({node, ...props}) => <h4 className="text-base mb-2" {...props} />,
          h5: ({node, ...props}) => <h5 className="text-sm mb-2" {...props} />,
          h6: ({node, ...props}) => <h6 className="text-sm mb-2" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-1" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-1" {...props} />,
          li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
          strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
          em: ({node, ...props}) => <em className="italic" {...props} />,
          code: ({node, ...props}) => <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...props} />,
          pre: ({node, ...props}) => <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4" {...props} />,
          blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground mb-4" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}