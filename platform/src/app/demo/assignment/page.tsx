export default function AssignmentPage() {
  return (
    <div className={"flex flex-row divide-x-2 h-full m-0"}>
      <div className={"w-3/4 p-5 h-full overflow-auto break-words"}>
        Really long text...
      </div>
      <div className={"sticky w-1/4 p-5 h-full overflow-auto break-words"}>
        sidebar here
      </div>
    </div>
  );
}