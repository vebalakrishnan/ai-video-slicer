import { useNavigate } from 'react-router-dom';
import { Alert, Badge, Heading, HStack, Text, VStack } from '@chakra-ui/react';
import { AnimatedList } from '../ui/AnimatedList';
import { GlassCard } from '../ui/GlassCard';
import type { ShortClip, VideoJob } from '../../types';

const CATEGORY_COLOR: Record<ShortClip['category'], string> = {
  viral: 'pink',
  educational: 'blue',
  emotional: 'purple',
  surprising: 'orange',
  story: 'teal',
  other: 'gray',
};

export interface ResultsGridProps {
  video: VideoJob;
  shorts: ShortClip[];
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Grid of scored short clips once a video job has produced results. Shows an
 * explanatory banner for `partial` jobs and an error state for `failed` ones.
 */
export function ResultsGrid({ video, shorts }: ResultsGridProps) {
  const navigate = useNavigate();

  return (
    <VStack align="stretch" gap={6}>
      {video.status === 'failed' && (
        <Alert.Root status="error" borderRadius="xl">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Processing failed</Alert.Title>
            <Alert.Description>
              {video.error_message ?? 'An unknown error occurred while processing this video.'}
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      )}

      {video.status === 'partial' && (
        <Alert.Root status="warning" borderRadius="xl">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Partial results</Alert.Title>
            <Alert.Description>
              {video.error_message ?? "We couldn't generate the full set of shorts for this video."}
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      )}

      {shorts.length === 0 ? (
        video.status !== 'failed' && <Text color="gray.500">No shorts generated yet.</Text>
      ) : (
        <AnimatedList>
          {shorts.map((short) => (
            <GlassCard
              key={short.id}
              mb={4}
              cursor="pointer"
              onClick={() => navigate(`/videos/${video.id}/shorts/${short.id}`)}
            >
              <HStack justify="space-between" align="start" gap={4}>
                <VStack align="start" gap={2} flex={1}>
                  <Heading size="sm">{short.title}</Heading>
                  <HStack gap={2}>
                    <Badge colorPalette={CATEGORY_COLOR[short.category]} borderRadius="full">
                      {short.category}
                    </Badge>
                    <Text fontSize="sm" color="gray.500">
                      {formatDuration(short.duration_seconds)}
                    </Text>
                  </HStack>
                </VStack>
                <VStack gap={0}>
                  <Text fontSize="2xl" fontWeight="bold" color="purple.500">
                    {short.overall_score.toFixed(1)}
                  </Text>
                  <Text fontSize="xs" color="gray.400">
                    score
                  </Text>
                </VStack>
              </HStack>
            </GlassCard>
          ))}
        </AnimatedList>
      )}
    </VStack>
  );
}
