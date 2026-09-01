import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../layout/AppLayout';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
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

  return <AppLayout>{children}</AppLayout>;
}
