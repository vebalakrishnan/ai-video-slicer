import type { ReactNode } from 'react';
import { AppHeader } from './AppHeader';

/**
 * Wraps every authenticated page with the persistent top nav. Applied once
 * inside ProtectedRoute/AdminRoute rather than per-page, so every current
 * and future protected route gets it automatically.
 */
export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AppHeader />
      {children}
    </>
  );
}
