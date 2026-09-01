import { Container, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MetricCards } from '../components/analytics/MetricCards';

/** Shows the current user's usage analytics (videos processed, shorts, scores). */
export function AnalyticsPage() {
  return (
    <PageWrapper>
      <Container maxW="6xl" py={10}>
        <Stack gap={8}>
          <Stack gap={1}>
            <Heading size="xl">Analytics</Heading>
            <Text color="gray.500">Your usage across the platform.</Text>
          </Stack>
          <MetricCards />
        </Stack>
      </Container>
    </PageWrapper>
  );
}

export default AnalyticsPage;
