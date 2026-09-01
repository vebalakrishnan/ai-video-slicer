import { Box, Grid, HStack, Progress, Text, VStack } from '@chakra-ui/react';
import { GlassCard } from '../ui/GlassCard';
import type { ShortClip } from '../../types';

type ScoreDimensionKey =
  | 'hook_strength'
  | 'standalone_value'
  | 'engagement'
  | 'retention'
  | 'payoff'
  | 'clarity'
  | 'shareability'
  | 'viral_potential'
  | 'b_roll_quality';

interface Dimension {
  key: ScoreDimensionKey;
  label: string;
}

const DIMENSIONS: Dimension[] = [
  { key: 'hook_strength', label: 'Hook Strength' },
  { key: 'standalone_value', label: 'Standalone Value' },
  { key: 'engagement', label: 'Engagement' },
  { key: 'retention', label: 'Retention' },
  { key: 'payoff', label: 'Payoff' },
  { key: 'clarity', label: 'Clarity' },
  { key: 'shareability', label: 'Shareability' },
  { key: 'viral_potential', label: 'Viral Potential' },
  { key: 'b_roll_quality', label: 'B-Roll Quality' },
];

export interface ScoreBreakdownProps {
  short: ShortClip;
}

/** Renders all 9 score dimensions (1-10) as labeled bars, plus the overall score. */
export function ScoreBreakdown({ short }: ScoreBreakdownProps) {
  return (
    <GlassCard>
      <VStack align="stretch" gap={5}>
        <HStack justify="space-between">
          <Text fontWeight="semibold" fontSize="lg">
            Score Breakdown
          </Text>
          <Text fontSize="2xl" fontWeight="bold" color="purple.500">
            {short.overall_score.toFixed(1)} / 10
          </Text>
        </HStack>

        <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={4}>
          {DIMENSIONS.map((dim) => {
            const value = short[dim.key];
            return (
              <Box key={dim.key}>
                <HStack justify="space-between" mb={1}>
                  <Text fontSize="sm">{dim.label}</Text>
                  <Text fontSize="sm" fontWeight="semibold">
                    {value}/10
                  </Text>
                </HStack>
                <Progress.Root value={value} min={0} max={10} colorPalette="pink" size="sm" borderRadius="full">
                  <Progress.Track>
                    <Progress.Range />
                  </Progress.Track>
                </Progress.Root>
              </Box>
            );
          })}
        </Grid>
      </VStack>
    </GlassCard>
  );
}
