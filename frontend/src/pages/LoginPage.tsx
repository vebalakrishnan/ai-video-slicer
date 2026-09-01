import { Center, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { LoginForm } from '../components/auth/LoginForm';

export function LoginPage() {
  return (
    <PageWrapper>
      <MeshBackground />
      <Center minH="100vh" px={4}>
        <GlassCard w="full" maxW="md">
          <Stack gap={6}>
            <Stack gap={1} textAlign="center">
              <Heading size="xl">Welcome Back</Heading>
              <Text color="gray.500" fontSize="sm">
                Sign in to continue to AI Video Slicer
              </Text>
            </Stack>
            <LoginForm />
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}

export default LoginPage;
