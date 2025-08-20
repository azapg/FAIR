import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
} from "@/components/ui/sidebar"

export function WorkflowsSidebar({
  side,
  className,
  ...sidebarProps
}: {
  side?: "left" | "right"
  className?: string
  [key: string]: any // eslint-disable-line @typescript-eslint/no-explicit-any
}) {
  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      <SidebarHeader />
      <SidebarContent>
        <SidebarGroup />
        hi
        <SidebarGroup />
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  )
}