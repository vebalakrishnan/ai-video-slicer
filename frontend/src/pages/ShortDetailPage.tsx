import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, Center, Container, Heading, Text, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { BRollTimeline } from '../components/video/BRollTimeline';
import { ScoreBreakdown } from '../components/video/ScoreBreakdown';
import { useBroll, useRenderShort, useShort, useShortVideoUrl } from '../hooks/useVideos';

export function ShortDetailPage() {
  const params = useParams<{ id: string; shortId: string }>();
  const shortId = params.shortId ? Number(params.shortId) : undefined;

  const { data: short, isLoading, isError } = useShort(shortId);
  const { data: broll } = useBroll(shortId);
  const renderShort = useRenderShort();

  // The download endpoint requires an Authorization header a plain
  // <video src>/<a href> can never send - this hook fetches it through the
  // authenticated API client and exposes a local blob: object URL instead.
  // Must run before any early return (Rules of Hooks), so it's driven off
  // optional-chained values rather than `short` directly.
  const isReady = short?.status === 'ready' && Boolean(short.file_path);
  const video = useShortVideoUrl(short?.id, isReady);

  // Read the aspect ratio from the actual loaded video (videoWidth/
  // videoHeight) rather than hardcoding one - stays correct no matter
  // what the backend renders (currently 1920x1080, previously 1080x1920).
  // Defaults to portrait (9:16) before metadata loads, since that's this
  // product's typical short-form output.
  const [videoAspectRatio, setVideoAspectRatio] = useState<string>('9 / 16');

  if (isError) {
    return (
      <PageWrapper>
        <Container maxW="3xl" py={10}>
          <Alert.Root status="error" borderRadius="lg">
            <Alert.Indicator />
            <Alert.Title>
              Couldn&apos;t load this clip. It may not exist, or you may not have access to it.
            </Alert.Title>
          </Alert.Root>
        </Container>
      </PageWrapper>
    );
  }

  if (isLoading || !short) {
    return (
      <PageWrapper>
        <Center minH="60vh">
          <Text color="gray.500">Loading clip…</Text>
        </Center>
      </PageWrapper>
    );
  }

  const canRender = short.status !== 'ready' && short.status !== 'rendering';

  const handleDownload = (): void => {
    if (!video.url) return;
    const link = document.createElement('a');
    link.href = video.url;
    link.download = `${short.title || 'short'}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <PageWrapper>
      <Container maxW="3xl" py={10}>
        <VStack align="stretch" gap={6}>
          <Heading size="lg">{short.title}</Heading>

          <GlassCard>
            <VStack align="stretch" gap={4}>
              {isReady && video.url ? (
                // eslint-disable-next-line jsx-a11y/media-has-caption
                <video
                  src={video.url}
                  controls
                  onLoadedMetadata={(e) => {
                    const { videoWidth, videoHeight } = e.currentTarget;
                    if (videoWidth > 0 && videoHeight > 0) {
                      setVideoAspectRatio(`${videoWidth} / ${videoHeight}`);
                    }
                  }}
                  style={{
                    display: 'block',
                    margin: '0 auto',
                    width: 'auto',
                    maxWidth: '100%',
                    height: 'auto',
                    maxHeight: '70vh',
                    aspectRatio: videoAspectRatio,
                    objectFit: 'contain',
                    backgroundColor: 'black',
                    borderRadius: '12px',
                  }}
                />
              ) : (
                <Center py={10} bg="blackAlpha.100" borderRadius="xl">
                  <Text color="gray.500">
                    {short.status === 'failed'
                      ? 'Rendering failed.'
                      : isReady && video.isLoading
                        ? 'Loading video…'
                        : isReady && video.isError
                          ? 'Could not load the rendered video.'
                          : 'Rendering not ready yet…'}
                  </Text>
                </Center>
              )}

              {canRender && (
                <GradientButton
                  onClick={() => renderShort.mutate(short.id)}
                  disabled={renderShort.isPending}
                >
                  {renderShort.isPending ? 'Starting Render…' : 'Render'}
                </GradientButton>
              )}

              <GradientButton onClick={handleDownload} disabled={!isReady || !video.url}>
                Download
              </GradientButton>
            </VStack>
          </GlassCard>

          <ScoreBreakdown short={short} />

          <GlassCard>
            <VStack align="stretch" gap={2}>
              <Text fontWeight="semibold">Transcript</Text>
              <Text color="gray.600">{short.transcript_excerpt}</Text>
            </VStack>
          </GlassCard>

          <GlassCard>
            <VStack align="stretch" gap={4}>
              <Text fontWeight="semibold">B-Roll Suggestions</Text>
              <BRollTimeline suggestions={broll ?? []} />
            </VStack>
          </GlassCard>
        </VStack>
      </Container>
    </PageWrapper>
  );
}
