import { HStack, Spinner, Text } from '@chakra-ui/react';
import { GlassCard } from '../ui/GlassCard';

/**
 * Shown for the brief window between clicking "Generate Shorts" and the
 * worker actually picking up the job (VideoJob.status is still "pending"
 * at this point - it only becomes "transcribing" once a Celery worker
 * starts it). Without this, the page looked identical to "not started yet"
 * even though the request had already succeeded, which read as frozen/stuck.
 */
export function QueuedStatus() {
  return (
    <GlassCard>
      <HStack gap={3}>
        <Spinner size="sm" color="purple.500" />
        <Text color="gray.600">Queued — waiting for a worker to pick this up…</Text>
      </HStack>
    </GlassCard>
  );
}
