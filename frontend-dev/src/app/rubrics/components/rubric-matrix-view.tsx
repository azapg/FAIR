import { RubricContent } from "@/hooks/use-rubrics";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function RubricMatrixView({ content }: { content: RubricContent }) {
  return (
    <div className="rounded-lg border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[24%]">Criterion</TableHead>
            <TableHead className="w-[10%]">Weight</TableHead>
            {content.levels.map((level, index) => (
              <TableHead key={`${level}-${index}`}>{level}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {content.criteria.map((criterion) => (
            <TableRow key={criterion.name}>
              <TableCell className="font-medium">{criterion.name}</TableCell>
              <TableCell>{Math.round(criterion.weight * 100)}%</TableCell>
              {criterion.levels.map((description, index) => (
                <TableCell key={`${criterion.name}-${index}`}>
                  {description}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
