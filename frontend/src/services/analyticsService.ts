import api from './api';
import type { AnalyticsOverview } from '../types';

/**
 * Thin wrapper around GET /analytics/overview — the current user's
 * aggregate usage metrics (videos processed, shorts generated, average
 * score, average processing time).
 */
export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  const { data } = await api.get<AnalyticsOverview>('/analytics/overview');
  return data;
}
