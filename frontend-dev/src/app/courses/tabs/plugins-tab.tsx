import {useTranslation} from "react-i18next";
import {usePlugins} from "@/hooks/use-plugins";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";

export function PluginsTab() {
  const {t} = useTranslation();
  const {data: plugins, isLoading, isError} = usePlugins();

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError) {
    return <div>{t("plugins.errorLoadingPlugins")}</div>;
  }

  if (!plugins || plugins.length === 0) {
    return <div className="text-sm text-muted-foreground">{t("plugins.empty")}</div>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("tabs.plugins")}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("assignments.titleLabel")}</TableHead>
            <TableHead>{t("plugins.type")}</TableHead>
            <TableHead>{t("plugins.version")}</TableHead>
            <TableHead>{t("plugins.author")}</TableHead>
            <TableHead>{t("plugins.source")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {plugins.map((plugin) => (
            <TableRow key={plugin.id}>
              <TableCell className="font-medium">{plugin.name}</TableCell>
              <TableCell className="capitalize">{plugin.type}</TableCell>
              <TableCell>{plugin.version}</TableCell>
              <TableCell>{plugin.author || "—"}</TableCell>
              <TableCell className="truncate max-w-[240px]">{plugin.source}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
