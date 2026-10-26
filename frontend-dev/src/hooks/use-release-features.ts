import { useSystemConfig } from "@/hooks/use-system-config";

export function useReleaseFeatures() {
  const config = useSystemConfig();
  const features = config.data?.features;
  // Never flash experiments while configuration is loading or unavailable.
  const nightly = config.data?.release_channel === "nightly";
  return {
    isPending: config.isPending,
    channel: nightly ? ("nightly" as const) : ("stable" as const),
    todo: nightly && features?.todo === true,
    inbox: nightly && features?.inbox === true,
    extensions: nightly && features?.extensions === true,
    course_content: nightly && features?.course_content === true,
    gradebook: nightly && features?.gradebook === true,
    dashboard:
      nightly &&
      features?.todo === true &&
      features?.course_content === true &&
      features?.gradebook === true,
  };
}
