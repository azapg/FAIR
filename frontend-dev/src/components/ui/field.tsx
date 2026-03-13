import * as React from 'react'

import { cn } from '@/lib/utils'
import { Label } from '@/components/ui/label'

function FieldGroup({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-4', className)} {...props} />
}

function Field({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return <div className={cn('grid gap-2', className)} {...props} />
}

function FieldLabel({
  className,
  ...props
}: React.ComponentProps<typeof Label>) {
  return <Label className={cn(className)} {...props} />
}

function FieldDescription({
  className,
  ...props
}: React.ComponentProps<'p'>) {
  return (
    <p
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  )
}

function FieldSeparator({
  className,
  children,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div className={cn('relative text-center text-sm', className)} {...props}>
      <div className="absolute inset-0 top-1/2 h-px -translate-y-1/2 bg-border" />
      <span className="relative bg-card px-2 text-muted-foreground">
        {children}
      </span>
    </div>
  )
}

export { Field, FieldDescription, FieldGroup, FieldLabel, FieldSeparator }
