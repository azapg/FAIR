import {Card, CardDescription, CardFooter, CardHeader, CardTitle} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Skeleton} from "@/components/ui/skeleton";

type Course = {
  id: string;
  title: string;
  description: string;
  color: string;
  instructors: string[];
  assignments: number;
}

// This is all AI-generated data for demonstration purposes.
const courses: Course[] = [
  {
    id: "course-1",
    title: "Introduction to Programming",
    description: "Learn the basics of programming with Python.",
    color: "blue",
    instructors: ["Alice Smith", "Bob Johnson"],
    assignments: 5,
  },
  {
    id: "course-2",
    title: "Data Structures and Algorithms",
    description: "Explore fundamental data structures and algorithms.",
    color: "amber",
    instructors: ["Charlie Brown"],
    assignments: 3,
  },
  {
    id: "course-3",
    title: "Web Development Fundamentals",
    description: "Build your first website using HTML, CSS, and JavaScript.",
    color: "red",
    instructors: ["Diana Prince", "Ethan Hunt"],
    assignments: 4,
  },
  {
    id: "course-4",
    title: "Machine Learning Basics",
    description: "An introduction to machine learning concepts and techniques.",
    color: "green",
    instructors: ["Frank Castle"],
    assignments: 2,
  },
  {
    id: "course-5",
    title: "Database Management Systems",
    description: "Learn how to design and manage databases effectively.",
    color: "purple",
    instructors: ["Grace Hopper", "Hank Pym"],
    assignments: 6,
  },
  {
    id: "course-6",
    title: "Mobile App Development",
    description: "Create your first mobile application for Android and iOS.",
    color: "pink",
    instructors: ["Ivy League"],
    assignments: 3,
  },
];

export default function CoursesPage() {
  return (
    <main>
      <div className={"flex items-center justify-between mb-6"}>
        <h1 className={"text-3xl"}>Your courses</h1>
        <Button>Create</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
        {courses.map((course) => (
          <Card key={course.id} className={`flex flex-col h-full bg-${course.color}-50 hover:bg-${course.color}-100 transition-colors cursor-pointer`}>
            <CardHeader className={"flex-1 flex flex-col items-start"}>
              <CardTitle>{course.title}</CardTitle>
              <CardDescription>{course.description}</CardDescription>
            </CardHeader>
            <CardFooter>{course.assignments} assignments.</CardFooter>
          </Card>
        ))}
      {/* Skeleton example */}
        <Card className={"bg-gray-50 cursor-wait flex flex-col h-full"}>
          <CardHeader className={"flex-1 flex flex-col items-start"}>
            <CardTitle>
              <Skeleton className="h-[20px] w-[300px] rounded-full bg-gray-200" />
            </CardTitle>
            <CardDescription className={"space-y-2 mt-2"}>
              <Skeleton className="h-4 w-[250px] bg-gray-200" />
              <Skeleton className="h-4 w-[200px] bg-gray-200" />
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Skeleton className="h-4 w-[150px] bg-gray-200" />
          </CardFooter>
        </Card>
      </div>
    </main>
  );
}