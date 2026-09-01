import { SimpleGrid, Stat, Text } from '@chakra-ui/react';
import { GlassCard } from '../ui/GlassCard';
import { useAnalyticsOverview } from '../../hooks/useAnalytics';

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return 'N/A';
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes}m ${remaining}s` : `${remaining}s`;
}

/**
 * Grid of GlassCard-based stat tiles showing the current user's
 * AnalyticsOverview metrics (videos processed, shorts generated, average
 * score, average processing time).
 */
export function MetricCards() {
  const { data, isLoading, isError } = useAnalyticsOverview();

  if (isLoading) {
    return <Text color="gray.500">Loading analytics...</Text>;
  }

  if (isError || !data) {
    return <Text color="red.500">Failed to load analytics.</Text>;
  }

  const metrics = [
    { label: 'Videos Processed', value: data.videos_processed },
    { label: 'Shorts Generated', value: data.shorts_generated },
    { label: 'Avg. Overall Score', value: data.avg_overall_score.toFixed(1) },
    {
      label: 'Avg. Processing Time',
      value: formatDuration(data.avg_processing_time_seconds),
    },
  ];

  return (
    <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} gap={6}>
      {metrics.map((metric) => (
        <GlassCard key={metric.label}>
          <Stat.Root>
            <Stat.Label color="gray.500">{metric.label}</Stat.Label>
            <Stat.ValueText
              fontSize="3xl"
              fontWeight="bold"
              bgGradient="to-r"
              gradientFrom="purple.500"
              gradientTo="pink.500"
              css={{ WebkitBackgroundClip: 'text', color: 'transparent' }}
            >
              {metric.value}
            </Stat.ValueText>
          </Stat.Root>
        </GlassCard>
      ))}
    </SimpleGrid>
  );
}
