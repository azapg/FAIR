import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/auth-context';

export default function Home() {
  const { isAuthenticated, loading } = useAuth();

  // Show nothing while loading authentication state
  if (loading) {
    return null;
  }

  // Redirect based on authentication state
  if (isAuthenticated) {
    return <Navigate to="/courses" replace />;
  }

  return <Navigate to="/login" replace />;
}
