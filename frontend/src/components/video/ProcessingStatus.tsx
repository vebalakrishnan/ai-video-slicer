import { Circle, HStack, Progress, Spinner, Text, VStack } from '@chakra-ui/react';
import { GlassCard } from '../ui/GlassCard';
import { useVideo } from '../../hooks/useVideos';
import type { VideoJobStatus } from '../../types';

interface Step {
  key: VideoJobStatus;
  label: string;
}

const STEPS: Step[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'transcribing', label: 'Transcribing' },
  { key: 'analyzing', label: 'Analyzing' },
  { key: 'rendering', label: 'Rendering' },
  { key: 'completed', label: 'Done' },
];

function stepIndex(status: VideoJobStatus): number {
  if (status === 'failed' || status === 'partial') {
    return STEPS.length - 1;
  }
  const idx = STEPS.findIndex((step) => step.key === status);
  return idx === -1 ? 0 : idx;
}

export interface ProcessingStatusProps {
  videoId: number;
}

/**
 * Simple stepper (Pending -> Transcribing -> Analyzing -> Rendering -> Done)
 * shown while a video job is still processing. Polls via useVideo internally.
 */
export function ProcessingStatus({ videoId }: ProcessingStatusProps) {
  const { data: video, isLoading } = useVideo(videoId);

  if (isLoading || !video) {
    return (
      <GlassCard>
        <Text color="gray.500">Loading status…</Text>
      </GlassCard>
    );
  }

  const activeIndex = stepIndex(video.status);
  const percent = ((activeIndex + 1) / STEPS.length) * 100;
  const isFailed = video.status === 'failed';

  return (
    <GlassCard>
      <VStack align="stretch" gap={6}>
        <HStack gap={3}>
          {!isFailed && <Spinner size="sm" color="purple.500" />}
          <Text fontWeight="semibold" fontSize="lg">
            {isFailed ? 'Processing failed' : 'Processing your video'}
          </Text>
        </HStack>

        <Progress.Root
          value={percent}
          min={0}
          max={100}
          colorPalette={isFailed ? 'red' : 'purple'}
          borderRadius="full"
        >
          <Progress.Track>
            <Progress.Range />
          </Progress.Track>
        </Progress.Root>

        <HStack justify="space-between" align="start">
          {STEPS.map((step, idx) => {
            const active = idx <= activeIndex;
            return (
              <VStack key={step.key} gap={2} flex={1}>
                <Circle
                  size="8"
                  bg={active ? (isFailed ? 'red.500' : 'purple.500') : 'gray.200'}
                  color="white"
                  fontSize="sm"
                  fontWeight="bold"
                >
                  {idx + 1}
                </Circle>
                <Text
                  fontSize="xs"
                  textAlign="center"
                  color={active ? (isFailed ? 'red.600' : 'purple.600') : 'gray.400'}
                >
                  {step.label}
                </Text>
              </VStack>
            );
          })}
        </HStack>
      </VStack>
    </GlassCard>
  );
}
