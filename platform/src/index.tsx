import { Routes, Route } from 'react-router-dom'
import Home from "./home";
import CoursesPage from "@/app/demo/courses/page";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path={"demo"} element={<CoursesPage />} />
      <Route path={"login"} element={<LoginPage />} />
      <Route path={"register"} element={<RegisterPage />} />
      <Route path="*" element={<div>Not Found</div>} />
    </Routes>
  )
}