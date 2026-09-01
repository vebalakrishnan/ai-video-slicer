import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../layout/AppLayout';

interface AdminRouteProps {
  children: ReactNode;
}

/**
 * Like ProtectedRoute, but additionally requires `user.is_admin`. A
 * signed-in non-admin user is redirected to /dashboard rather than /login.
 */
export function AdminRoute({ children }: AdminRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Center minH="100vh">
        <Spinner size="xl" color="purple.500" />
      </Center>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
}
