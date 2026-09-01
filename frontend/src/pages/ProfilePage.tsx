import { Center, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { ProfileForm } from '../components/auth/ProfileForm';

// Authenticated app page (not a landing/auth page) — no MeshBackground.
export function ProfilePage() {
  return (
    <PageWrapper>
      <Center minH="100vh" px={4}>
        <GlassCard w="full" maxW="md">
          <Stack gap={6}>
            <Stack gap={1} textAlign="center">
              <Heading size="xl">Your Profile</Heading>
              <Text color="gray.500" fontSize="sm">
                Manage your account details
              </Text>
            </Stack>
            <ProfileForm />
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}

export default ProfilePage;
