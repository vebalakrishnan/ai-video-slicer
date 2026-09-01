import { Badge, HStack, Link, Text, VStack } from '@chakra-ui/react';
import { AnimatedList } from '../ui/AnimatedList';
import { GlassCard } from '../ui/GlassCard';
import type { BRollSuggestion } from '../../types';

const VISUAL_TYPE_LABEL: Record<BRollSuggestion['visual_type'], string> = {
  stock_footage: 'Stock Footage',
  image: 'Image',
  screenshot: 'Screenshot',
  screen_recording: 'Screen Recording',
  chart: 'Chart',
  animation: 'Animation',
};

export interface BRollTimelineProps {
  suggestions: BRollSuggestion[];
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** List of B-roll suggestions for a short clip, with timestamp range and asset link. */
export function BRollTimeline({ suggestions }: BRollTimelineProps) {
  if (suggestions.length === 0) {
    return <Text color="gray.500">No B-roll suggestions yet.</Text>;
  }

  return (
    <AnimatedList>
      {suggestions.map((item) => (
        <GlassCard key={item.id} mb={3}>
          <VStack align="stretch" gap={2}>
            <HStack justify="space-between">
              <Text fontWeight="semibold" fontSize="sm">
                {formatTime(item.start_time)} – {formatTime(item.end_time)}
              </Text>
              <Badge colorPalette="purple" borderRadius="full">
                {VISUAL_TYPE_LABEL[item.visual_type]}
              </Badge>
            </HStack>
            <Text fontSize="sm">{item.description}</Text>
            <Text fontSize="xs" color="gray.500">
              Keywords: {item.search_keywords}
            </Text>
            {item.stock_asset_url && (
              <Link href={item.stock_asset_url} target="_blank" rel="noopener noreferrer" color="purple.500" fontSize="sm">
                View asset
              </Link>
            )}
          </VStack>
        </GlassCard>
      ))}
    </AnimatedList>
  );
}
