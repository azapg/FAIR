import { Navigate, Route, Routes } from "react-router-dom";
import Home from "@/home";
import CoursesPage from "@/app/courses/page";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import CourseDetailPage from "@/app/courses/course/page";
import AssignmentPage from "@/app/assignment/page";
import RubricsPage from "@/app/rubrics/page";
import JobsLabPage from "@/app/jobs-lab/page";
import AdminLabPage from "@/app/admin-lab/page";
import { IfSetting } from "@/components/if-setting";

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
      <Route
        path={"jobs-lab"}
        element={
          <IfSetting setting="ui.devMode" scope="local-first" fallback={<Navigate to="/courses" replace />}>
            <JobsLabPage />
          </IfSetting>
        }
      />
      <Route
        path={"admin-lab"}
        element={
          <IfSetting setting="ui.devMode" scope="local-first" fallback={<Navigate to="/courses" replace />}>
            <AdminLabPage />
          </IfSetting>
        }
      />

      <Route path={"login"} element={<LoginPage/>}/>
      <Route path={"register"} element={<RegisterPage/>}/>

      <Route path="*" element={<div>Not Found</div>}/>
    </Routes>
  )
}
