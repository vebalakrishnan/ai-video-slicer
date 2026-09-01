import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getAnalyticsOverview } from '../services/analyticsService';
import type { AnalyticsOverview } from '../types';

/** Fetches the current user's analytics overview metrics. */
export function useAnalyticsOverview(): UseQueryResult<AnalyticsOverview> {
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: getAnalyticsOverview,
  });
}
