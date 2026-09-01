import { useParams } from 'react-router-dom';
import { Alert, Center, Container, Heading, Text, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { ProcessingStatus } from '../components/video/ProcessingStatus';
import { QueuedStatus } from '../components/video/QueuedStatus';
import { ResultsGrid } from '../components/video/ResultsGrid';
import { useGenerateShorts, useShorts, useVideo } from '../hooks/useVideos';
import type { VideoJobStatus } from '../types';

// "pending" is handled separately below (it splits into "not dispatched
// yet" vs "dispatched, queued for a worker") - it's never treated the same
// as the actively-running steps here.
const ACTIVE_STATUSES: readonly VideoJobStatus[] = ['transcribing', 'analyzing', 'rendering'];
const TERMINAL_STATUSES: readonly VideoJobStatus[] = ['completed', 'partial', 'failed'];

export function VideoStatusPage() {
  const params = useParams<{ id: string }>();
  const videoId = params.id ? Number(params.id) : undefined;

  const { data: video, isLoading, isError } = useVideo(videoId);
  const generateShorts = useGenerateShorts();

  const isActive = video ? ACTIVE_STATUSES.includes(video.status) : false;
  const isTerminal = video ? TERMINAL_STATUSES.includes(video.status) : false;
  // Dispatched this session but the worker hasn't flipped the status past
  // "pending" yet - still worth its own "queued" indicator rather than
  // silence, since the button-click already succeeded.
  const isQueued =
    video?.status === 'pending' && (generateShorts.isPending || generateShorts.isSuccess);

  const { data: shorts } = useShorts(video && isTerminal ? videoId : undefined);

  if (isError) {
    return (
      <PageWrapper>
        <Container maxW="4xl" py={10}>
          <Alert.Root status="error" borderRadius="lg">
            <Alert.Indicator />
            <Alert.Title>
              Couldn&apos;t load this video. It may not exist, or you may not have access to it.
            </Alert.Title>
          </Alert.Root>
        </Container>
      </PageWrapper>
    );
  }

  if (isLoading || !video) {
    return (
      <PageWrapper>
        <Center minH="60vh">
          <Text color="gray.500">Loading video…</Text>
        </Center>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <Container maxW="4xl" py={10}>
        <VStack align="stretch" gap={6}>
          <Heading size="lg">{video.title ?? 'Video'}</Heading>

          {video.status === 'pending' && !isQueued && (
            <GlassCard>
              <VStack align="start" gap={3}>
                <Text>Ready to find the best short-form clips from this video.</Text>
                <GradientButton
                  onClick={() => generateShorts.mutate(video.id)}
                  disabled={generateShorts.isPending}
                >
                  {generateShorts.isPending ? 'Starting…' : 'Generate Shorts'}
                </GradientButton>
              </VStack>
            </GlassCard>
          )}

          {isQueued && <QueuedStatus />}
          {isActive && <ProcessingStatus videoId={video.id} />}
          {isTerminal && <ResultsGrid video={video} shorts={shorts ?? []} />}
        </VStack>
      </Container>
    </PageWrapper>
  );
}
