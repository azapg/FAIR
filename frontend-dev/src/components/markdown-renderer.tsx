import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';

interface MarkdownRendererProps {
  children: string;
  className?: string;
  compact?: boolean;
  allowSafeHtml?: boolean;

  /**
   * Enable built-in truncation with expand/collapse UI.
   */
  clamp?: boolean;

  /**
   * Max number of lines before clamp is considered "overflowing".
   * Default: 3
   */
  clampLines?: number;

  /**
   * Max number of words before clamp is considered "overflowing".
   * Default: 80
   */
  clampWords?: number;

  /**
   * Optional custom labels for toggle button.
   */
  showMoreLabel?: React.ReactNode;
  showLessLabel?: React.ReactNode;

  /**
   * Optional className for the toggle button.
   */
  buttonClassName?: string;
}

function isSafeImageSrc(src: string) {
  try {
    return new URL(src).protocol === 'https:';
  } catch {
    return false;
  }
}

function htmlNodeToMarkdownNodes(html: string): any[] {
  if (typeof DOMParser === 'undefined') {
    return [];
  }

  const doc = new DOMParser().parseFromString(html, 'text/html');

  const convertNode = (node: Node): any[] => {
    if (node.nodeType === Node.TEXT_NODE) {
      const value = node.textContent ?? '';
      return value ? [{ type: 'text', value }] : [];
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return [];
    }

    const element = node as HTMLElement;
    const tagName = element.tagName.toLowerCase();

    if (tagName === 'img') {
      const src = element.getAttribute('src') ?? '';
      const title = element.getAttribute('title');
      if (!isSafeImageSrc(src)) {
        return [];
      }

      return [
        {
          type: 'image',
          url: src,
          alt: element.getAttribute('alt') ?? '',
          title,
        },
      ];
    }

    if (tagName === 'br') {
      return [{ type: 'break' }];
    }

    if (tagName === 'div' || tagName === 'span' || tagName === 'p') {
      return Array.from(element.childNodes).flatMap(convertNode);
    }

    return [];
  };

  return Array.from(doc.body.childNodes).flatMap(convertNode);
}

function remarkSafeLogHtml() {
  return (tree: any) => {
    const visit = (node: any) => {
      if (!node || !Array.isArray(node.children)) {
        return;
      }

      node.children = node.children.flatMap((child: any) => {
        if (child?.type === 'html' && typeof child.value === 'string') {
          return htmlNodeToMarkdownNodes(child.value);
        } else {
          visit(child);
          return [child];
        }
      });
    };

    visit(tree);
  };
}

export function MarkdownRenderer({
  children,
  className,
  compact,
  allowSafeHtml,
  clamp = false,
  clampLines = 3,
  clampWords = 80,
  showMoreLabel,
  showLessLabel,
  buttonClassName,
}: MarkdownRendererProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const resolvedShowMoreLabel = showMoreLabel ?? t('common.showMore');
  const resolvedShowLessLabel = showLessLabel ?? t('common.showLess');

  const { hasMore } = useMemo(() => {
    if (!clamp || !children) {
      return { hasMore: false };
    }

    const lineCount = children.split('\n').length;
    const wordCount = children.trim().split(/\s+/).filter(Boolean).length;

    return {
      hasMore: lineCount > clampLines || wordCount > clampWords,
    };
  }, [children, clamp, clampLines, clampWords]);

  const shouldClampNow = clamp && hasMore && !isExpanded;

  return (
    <>
      <div
        className={cn(
          'markdown-content',
          className,
          shouldClampNow && 'relative overflow-hidden'
        )}
        style={
          shouldClampNow
            ? {
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
                WebkitLineClamp: clampLines,
              }
            : undefined
        }
      >
        <ReactMarkdown
          remarkPlugins={allowSafeHtml ? [remarkMath, remarkSafeLogHtml] : [remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            h1: ({ node, ...props }) => (
              <h1 className={cn('text-2xl', !compact && 'mb-4')} {...props} />
            ),
            p: ({ node, ...props }) => (
              <p className={cn('leading-relaxed', !compact && 'mb-4')} {...props} />
            ),
            h2: ({ node, ...props }) => (
              <h2 className={cn('text-xl', !compact && 'mb-3')} {...props} />
            ),
            h3: ({ node, ...props }) => (
              <h3 className={cn('text-lg', !compact && 'mb-2')} {...props} />
            ),
            h4: ({ node, ...props }) => (
              <h4 className={cn('text-base', !compact && 'mb-2')} {...props} />
            ),
            h5: ({ node, ...props }) => (
              <h5 className={cn('text-sm', !compact && 'mb-2')} {...props} />
            ),
            h6: ({ node, ...props }) => (
              <h6 className={cn('text-sm', !compact && 'mb-2')} {...props} />
            ),
            ul: ({ node, ...props }) => (
              <ul className={cn('list-disc list-inside space-y-1', !compact && 'mb-4')} {...props} />
            ),
            ol: ({ node, ...props }) => (
              <ol
                className={cn('list-decimal list-inside space-y-1', !compact && 'mb-4')}
                {...props}
              />
            ),
            li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
            strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
            em: ({ node, ...props }) => <em className="italic" {...props} />,
            code: ({ node, ...props }) => (
              <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...props} />
            ),
            pre: ({ node, ...props }) => (
              <pre
                className={cn('bg-muted p-4 rounded-lg overflow-x-auto', !compact && 'mb-4')}
                {...props}
              />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote
                className={cn(
                  'border-l-4 border-primary pl-4 italic text-muted-foreground',
                  !compact && 'mb-4'
                )}
                {...props}
              />
            ),
          }}
        >
          {children}
        </ReactMarkdown>

        {shouldClampNow && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-background to-transparent pointer-events-none" />
        )}
      </div>

      {clamp && hasMore && (
        <Button
          variant="link"
          size="sm"
          onClick={() => setIsExpanded((prev) => !prev)}
          className={cn('p-0 h-auto text-sm', buttonClassName)}
        >
          {isExpanded ? resolvedShowLessLabel : resolvedShowMoreLabel}
        </Button>
      )}
    </>
  );
}