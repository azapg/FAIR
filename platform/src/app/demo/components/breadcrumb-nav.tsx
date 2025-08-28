import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from "@/components/ui/breadcrumb";
import Link from "next/link";
import React from "react";

export type BreadcrumbSegment = {
  label: string;
  slug: string;
  isLast?: boolean;
}

// Add a typed crumb shape for internal use
type Crumb = {
  label: string;
  href: string;
  isLast: boolean;
};

// Normalize and strongly type the generator
const generateBreadcrumbs = (baseUrl: string, segments: BreadcrumbSegment[]): Crumb[] => {
  const normalizeBase = (s: string) => {
    if (!s || s === "/") return "";
    return `/${s}`.replace(/\/+/g, "/").replace(/\/$/, "");
  };

  const crumbs: Array<Omit<Crumb, "isLast">> = [{ label: "Home", href: "/" }];

  let currentPath = normalizeBase(baseUrl);

  segments.forEach((segment) => {
    const slug = String(segment.slug).replace(/^\/+|\/+$/g, "");
    currentPath = `${currentPath}/${slug}`.replace(/\/+/g, "/");
    crumbs.push({
      label: segment.label,
      href: currentPath
    });
  });

  const lastIndex = crumbs.length - 1;
  return crumbs.map((c, i) => ({ ...c, isLast: i === lastIndex }));
};

export function BreadcrumbNav({className, segments, baseUrl = ""}: { className?: string, baseUrl?: string, segments: BreadcrumbSegment[] }) {
  const breadcrumbs = React.useMemo(() => generateBreadcrumbs(baseUrl, segments ?? []), [baseUrl, segments]);
  return (
    <Breadcrumb className={className}>
      <BreadcrumbList>
        {breadcrumbs.map((crumb) => (
          <React.Fragment key={crumb.href}>
            <BreadcrumbItem>
              {crumb.isLast ? (
                <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink asChild>
                  <Link href={crumb.href}>{crumb.label}</Link>
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
            {!crumb.isLast && <BreadcrumbSeparator />}
          </React.Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}