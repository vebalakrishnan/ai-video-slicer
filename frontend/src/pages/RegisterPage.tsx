import { Center, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { RegisterForm } from '../components/auth/RegisterForm';

export function RegisterPage() {
  return (
    <PageWrapper>
      <MeshBackground />
      <Center minH="100vh" px={4}>
        <GlassCard w="full" maxW="md">
          <Stack gap={6}>
            <Stack gap={1} textAlign="center">
              <Heading size="xl">Create Your Account</Heading>
              <Text color="gray.500" fontSize="sm">
                Start slicing your videos with AI
              </Text>
            </Stack>
            <RegisterForm />
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}

export default RegisterPage;
