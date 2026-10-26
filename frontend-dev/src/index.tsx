import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useReleaseFeatures } from "@/hooks/use-release-features";
import type { ReactNode } from "react";

function FeatureRoute({
  feature,
  children,
}: {
  feature: "todo" | "extensions" | "dashboard";
  children: ReactNode;
}) {
  const flags = useReleaseFeatures();
  if (flags.isPending) return <RouteFallback />;
  return flags[feature] ? children : <Navigate to="/courses" replace />;
}

const Home = lazy(() => import("@/home"));
const CoursesPage = lazy(() => import("@/app/courses/page"));
const LoginPage = lazy(() => import("@/app/login/page"));
const RegisterPage = lazy(() => import("@/app/register/page"));
const ForgotPasswordPage = lazy(() => import("@/app/forgot-password/page"));
const ResetPasswordPage = lazy(() => import("@/app/reset-password/page"));
const VerifyEmailPage = lazy(() => import("@/app/verify-email/page"));
const CourseDetailPage = lazy(() => import("@/app/courses/course/page"));
const AssignmentPage = lazy(() => import("@/app/assignment/page"));
const RubricsPage = lazy(() => import("@/app/rubrics/page"));
const ExtensionsPage = lazy(() => import("@/app/extensions/page"));
const ExtensionDetailPage = lazy(
  () => import("@/app/extensions/extension/page"),
);
const ChatDemoPage = lazy(() => import("@/app/chat/page"));
const LiveChatPage = lazy(() => import("@/app/chat/live-page"));
const TodoPage = lazy(() => import("@/app/todo/page"));
const StudentDashboardPage = lazy(() => import("@/app/dashboard/page"));

function RouteFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-32 items-center justify-center text-sm text-muted-foreground"
    >
      Loading…
    </div>
  );
}

export function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="chat" element={<LiveChatPage />} />
        <Route path="chat/live" element={<LiveChatPage />} />
        {import.meta.env.DEV && (
          <Route path="chat/demo" element={<ChatDemoPage />} />
        )}

        <Route path="courses" element={<CoursesPage />} />
        <Route
          path="todo"
          element={
            <FeatureRoute feature="todo">
              <TodoPage />
            </FeatureRoute>
          }
        />
        <Route
          path="dashboard"
          element={
            <FeatureRoute feature="dashboard">
              <StudentDashboardPage />
            </FeatureRoute>
          }
        />
        <Route path="courses/:courseId" element={<CourseDetailPage />} />
        <Route path="courses/:courseId/" element={<CourseDetailPage />} />
        <Route path="courses/:courseId/:tab" element={<CourseDetailPage />} />
        <Route
          path="courses/:courseId/assignments/:assignmentId"
          element={<AssignmentPage />}
        />
        <Route path="rubrics" element={<RubricsPage />} />
        <Route
          path="extensions"
          element={
            <FeatureRoute feature="extensions">
              <ExtensionsPage />
            </FeatureRoute>
          }
        />
        <Route
          path="extensions/:id"
          element={
            <FeatureRoute feature="extensions">
              <ExtensionDetailPage />
            </FeatureRoute>
          }
        />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="verify-email" element={<VerifyEmailPage />} />

        <Route path="*" element={<div>Not Found</div>} />
      </Routes>
    </Suspense>
  );
}
