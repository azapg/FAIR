declare module "markdown-truncate" {
  export default function truncate(
    value: string,
    options?: { limit?: number; ellipsis?: string },
  ): string;
}
