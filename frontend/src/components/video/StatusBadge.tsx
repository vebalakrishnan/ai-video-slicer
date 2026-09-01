import { Badge, Spinner } from '@chakra-ui/react';
import type { VideoJobStatus } from '../../types';

interface StatusConfig {
  label: string;
  colorPalette: string;
  spinning: boolean;
}

const STATUS_CONFIG: Record<VideoJobStatus, StatusConfig> = {
  pending: { label: 'Pending', colorPalette: 'gray', spinning: false },
  transcribing: { label: 'Transcribing', colorPalette: 'blue', spinning: true },
  analyzing: { label: 'Analyzing', colorPalette: 'blue', spinning: true },
  rendering: { label: 'Rendering', colorPalette: 'blue', spinning: true },
  completed: { label: 'Completed', colorPalette: 'green', spinning: false },
  partial: { label: 'Partial', colorPalette: 'orange', spinning: false },
  failed: { label: 'Failed', colorPalette: 'red', spinning: false },
};

export interface StatusBadgeProps {
  status: VideoJobStatus;
}

/** Small colored badge mapping a VideoJob status to a color + spinner. */
export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge
      colorPalette={config.colorPalette}
      borderRadius="full"
      px={3}
      py={1}
      display="inline-flex"
      alignItems="center"
      gap={1.5}
    >
      {config.spinning && <Spinner size="xs" />}
      {config.label}
    </Badge>
  );
}
