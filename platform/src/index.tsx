import { Routes, Route, Navigate } from 'react-router-dom';
import Home from "@/home";
import CoursesPage from "@/app/courses/page";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import CourseDetailPage from "@/app/courses/course/page";
import DemoAssignmentPage from "@/app/assignment/demo";
import AssignmentPage from "@/app/assignment/page";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Home/>}/>

      <Route path={"demo"} element={<Navigate to="/demo/courses" replace/>}  />
      <Route path={"demo"}>
        <Route path={"courses"} element={<CoursesPage/>}/>
        {/*TODO:i should probably redirect to :assignments for consistency*/}
        <Route path={"courses/:courseId/"} element={<CourseDetailPage/>}/>
        <Route path={"courses/:courseId/:tab"} element={<CourseDetailPage/>}/>
        <Route path={"courses/:courseId/assignments/:assignmentId"} element={<AssignmentPage />} />

        <Route path={"assignment"} element={<DemoAssignmentPage />} />
      </Route>

      <Route path={"login"} element={<LoginPage/>}/>
      <Route path={"register"} element={<RegisterPage/>}/>

      <Route path="*" element={<div>Not Found</div>}/>
    </Routes>
  )
}