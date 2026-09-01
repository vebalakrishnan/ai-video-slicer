import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Box, Flex, HStack, chakra } from '@chakra-ui/react';
import { useAuth } from '../../context/AuthContext';
import { GradientButton } from '../ui/GradientButton';

const StyledLink = chakra(RouterLink);

interface NavItem {
  to: string;
  label: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/videos/new', label: 'New Video' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/admin', label: 'Admin', adminOnly: true },
];

/**
 * Persistent top navigation shown on every authenticated page (wired in via
 * ProtectedRoute/AdminRoute, not per-page) - without it, a page like the
 * dashboard had no way to reach /videos/new, /analytics, /admin, /profile,
 * or log out except by typing a URL directly.
 */
export function AppHeader() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = (): void => {
    logout();
    navigate('/login');
  };

  const visibleNavItems = NAV_ITEMS.filter((item) => !item.adminOnly || user?.is_admin);

  return (
    <Box
      as="header"
      position="sticky"
      top={0}
      zIndex={10}
      bg="white"
      borderBottomWidth="1px"
      borderColor="gray.100"
    >
      <Flex maxW="6xl" mx="auto" px={6} py={3} align="center" justify="space-between" gap={6}>
        <StyledLink
          to="/dashboard"
          fontWeight="bold"
          fontSize="lg"
          whiteSpace="nowrap"
          bgGradient="to-r"
          gradientFrom="purple.500"
          gradientTo="pink.500"
          bgClip="text"
        >
          AI Video Slicer
        </StyledLink>

        <HStack gap={6} flex={1} overflowX="auto">
          {visibleNavItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to);
            return (
              <StyledLink
                key={item.to}
                to={item.to}
                fontSize="sm"
                fontWeight={isActive ? 'semibold' : 'medium'}
                color={isActive ? 'purple.600' : 'gray.600'}
                _hover={{ color: 'purple.500' }}
              >
                {item.label}
              </StyledLink>
            );
          })}
        </HStack>

        <HStack gap={4}>
          <StyledLink
            to="/profile"
            fontSize="sm"
            color="gray.600"
            display={{ base: 'none', sm: 'inline' }}
            _hover={{ color: 'purple.500' }}
          >
            {user?.email}
          </StyledLink>
          <GradientButton onClick={handleLogout} px={4} py={2} fontSize="sm">
            Log Out
          </GradientButton>
        </HStack>
      </Flex>
    </Box>
  );
}
