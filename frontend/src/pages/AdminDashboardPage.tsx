import { Link as RouterLink } from 'react-router-dom';
import {
  chakra,
  Container,
  Heading,
  SimpleGrid,
  Stack,
  Stat,
  Text,
} from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { useAdminStats } from '../hooks/useAdmin';

const StyledRouterLink = chakra(RouterLink);

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return 'N/A';
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes}m ${remaining}s` : `${remaining}s`;
}

/** Platform-wide stats overview (admin only). */
export function AdminDashboardPage() {
  const { data, isLoading, isError } = useAdminStats();

  return (
    <PageWrapper>
      <Container maxW="6xl" py={10}>
        <Stack gap={8}>
          <Stack gap={1}>
            <Heading size="xl">Admin Dashboard</Heading>
            <Text color="gray.500">
              Platform-wide usage stats.{' '}
              <StyledRouterLink
                to="/admin/users"
                color="purple.500"
                fontWeight="semibold"
              >
                Manage users →
              </StyledRouterLink>
            </Text>
          </Stack>

          {isLoading && <Text color="gray.500">Loading stats...</Text>}
          {isError && <Text color="red.500">Failed to load platform stats.</Text>}

          {data && (
            <>
              <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} gap={6}>
                <GlassCard>
                  <Stat.Root>
                    <Stat.Label color="gray.500">Total Users</Stat.Label>
                    <Stat.ValueText fontSize="3xl" fontWeight="bold">
                      {data.total_users}
                    </Stat.ValueText>
                  </Stat.Root>
                </GlassCard>
                <GlassCard>
                  <Stat.Root>
                    <Stat.Label color="gray.500">Total Video Jobs</Stat.Label>
                    <Stat.ValueText fontSize="3xl" fontWeight="bold">
                      {data.total_video_jobs}
                    </Stat.ValueText>
                  </Stat.Root>
                </GlassCard>
                <GlassCard>
                  <Stat.Root>
                    <Stat.Label color="gray.500">Success Rate</Stat.Label>
                    <Stat.ValueText fontSize="3xl" fontWeight="bold">
                      {(data.success_rate * 100).toFixed(1)}%
                    </Stat.ValueText>
                  </Stat.Root>
                </GlassCard>
                <GlassCard>
                  <Stat.Root>
                    <Stat.Label color="gray.500">Avg. Processing Time</Stat.Label>
                    <Stat.ValueText fontSize="3xl" fontWeight="bold">
                      {formatDuration(data.avg_processing_time_seconds)}
                    </Stat.ValueText>
                  </Stat.Root>
                </GlassCard>
              </SimpleGrid>

              <GlassCard>
                <Stack gap={3}>
                  <Heading size="md">Jobs by Status</Heading>
                  <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
                    {Object.entries(data.jobs_by_status).map(([status, count]) => (
                      <Stack key={status} gap={0}>
                        <Text
                          fontSize="sm"
                          color="gray.500"
                          textTransform="capitalize"
                        >
                          {status}
                        </Text>
                        <Text fontSize="xl" fontWeight="bold">
                          {count}
                        </Text>
                      </Stack>
                    ))}
                  </SimpleGrid>
                </Stack>
              </GlassCard>
            </>
          )}
        </Stack>
      </Container>
    </PageWrapper>
  );
}

export default AdminDashboardPage;
