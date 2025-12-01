import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from "@/components/ui/breadcrumb";
import {Link} from "react-router-dom";
import React from "react";
import { useTranslation } from "react-i18next";

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
const generateBreadcrumbs = (baseUrl: string, segments: BreadcrumbSegment[], home: string = "Home"): Crumb[] => {
  const normalizeBase = (s: string) => {
    if (!s || s === "/") return "";
    return `/${s}`.replace(/\/+/g, "/").replace(/\/$/, "");
  };

  const crumbs: Array<Omit<Crumb, "isLast">> = [{ label: home, href: "/" }];

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
  const { t } = useTranslation();

  const breadcrumbs = React.useMemo(() => generateBreadcrumbs(baseUrl, segments ?? [], t("common.home")), [baseUrl, segments, t]);
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
                  <Link to={crumb.href}>{crumb.label}</Link>
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