import { useNavigate } from 'react-router-dom';
import { Center, Heading, HStack, Text, VStack } from '@chakra-ui/react';
import { AnimatedList } from '../ui/AnimatedList';
import { GlassCard } from '../ui/GlassCard';
import { StatusBadge } from './StatusBadge';
import type { VideoJob } from '../../types';

export interface VideoJobListProps {
  videos: VideoJob[];
  isLoading?: boolean;
}

function sourceLabel(video: VideoJob): string {
  if (video.source_type === 'url') {
    return video.source_url ?? 'Video URL';
  }
  return video.file_path ?? 'Uploaded file';
}

/** List of the current user's video jobs, each row navigating to its status page. */
export function VideoJobList({ videos, isLoading = false }: VideoJobListProps) {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Center py={12}>
        <Text color="gray.500">Loading videos…</Text>
      </Center>
    );
  }

  if (videos.length === 0) {
    return (
      <Center py={12}>
        <Text color="gray.500">No videos yet. Submit one to get started.</Text>
      </Center>
    );
  }

  return (
    <AnimatedList>
      {videos.map((video) => (
        <GlassCard
          key={video.id}
          mb={4}
          cursor="pointer"
          onClick={() => navigate(`/videos/${video.id}`)}
        >
          <HStack justify="space-between" align="start" gap={4}>
            <VStack align="start" gap={1}>
              <Heading size="sm">{video.title ?? sourceLabel(video)}</Heading>
              <Text fontSize="sm" color="gray.500">
                {sourceLabel(video)}
              </Text>
              <Text fontSize="xs" color="gray.400">
                {new Date(video.created_at).toLocaleString()}
              </Text>
            </VStack>
            <StatusBadge status={video.status} />
          </HStack>
        </GlassCard>
      ))}
    </AnimatedList>
  );
}
