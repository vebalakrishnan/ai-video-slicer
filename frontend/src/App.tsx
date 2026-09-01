import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { system } from './lib/theme';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AdminRoute } from './components/admin/AdminRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ProfilePage } from './pages/ProfilePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewVideoPage } from './pages/NewVideoPage';
import { VideoStatusPage } from './pages/VideoStatusPage';
import { ShortDetailPage } from './pages/ShortDetailPage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <ChakraProvider value={system}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Phase 2 module agents: add <Route> entries here, e.g.
                  <Route path="/login" element={<PageWrapper><LoginPage /></PageWrapper>} />
                  <Route path="/dashboard" element={<ProtectedRoute><PageWrapper><DashboardPage /></PageWrapper></ProtectedRoute>} />
              */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analytics"
                element={
                  <ProtectedRoute>
                    <AnalyticsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <AdminDashboardPage />
                  </AdminRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <AdminRoute>
                    <AdminUsersPage />
                  </AdminRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/videos/new"
                element={
                  <ProtectedRoute>
                    <NewVideoPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/videos/:id"
                element={
                  <ProtectedRoute>
                    <VideoStatusPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/videos/:id/shorts/:shortId"
                element={
                  <ProtectedRoute>
                    <ShortDetailPage />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ChakraProvider>
  );
}
