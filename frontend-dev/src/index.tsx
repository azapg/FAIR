import { Route, Routes } from "react-router-dom";
import Home from "@/home";
import CoursesPage from "@/app/courses/page";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import ForgotPasswordPage from "@/app/forgot-password/page";
import CourseDetailPage from "@/app/courses/course/page";
import AssignmentPage from "@/app/assignment/page";
import RubricsPage from "@/app/rubrics/page";
import { IfSetting } from "@/components/if-setting";
import ExtensionsPage from "@/app/extensions/page";
import ExtensionDetailPage from "@/app/extensions/extension/page";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Home/>}/>

      <Route path={"courses"} element={<CoursesPage/>}/>
      <Route path={"courses/:courseId"} element={<CourseDetailPage/>}/>
      <Route path={"courses/:courseId/"} element={<CourseDetailPage/>}/>
      <Route path={"courses/:courseId/:tab"} element={<CourseDetailPage/>}/>
      <Route path={"courses/:courseId/assignments/:assignmentId"} element={<AssignmentPage/>}/>
      <Route path={"rubrics"} element={<RubricsPage/>}/>
      <Route path={"extensions"} element={<ExtensionsPage/>}/>
      <Route path={"extensions/:id"} element={<ExtensionDetailPage/>}/>
      <Route path={"login"} element={<LoginPage/>}/>
      <Route path={"register"} element={<RegisterPage/>}/>
      <Route path={"forgot-password"} element={<ForgotPasswordPage/>}/>

      <Route path="*" element={<div>Not Found</div>}/>
    </Routes>
  )
}
