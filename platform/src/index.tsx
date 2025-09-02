import { Routes, Route } from 'react-router-dom'
import Home from "./home";
import CoursesPage from "@/app/demo/courses/page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path={"demo"} element={<CoursesPage />} />
      <Route path="*" element={<div>Not Found</div>} />
    </Routes>
  )
}