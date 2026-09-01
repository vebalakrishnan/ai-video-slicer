// Shared TypeScript types for the AI Video Slicer frontend.
//
// Phase 1 (Foundation) only defines the core `User` type needed by
// AuthContext / ProtectedRoute. Phase 2 module agents (video upload,
// dashboard, editor, etc.) should add their domain types here — e.g.
// VideoJob, ShortClip, BRollSuggestion — rather than creating ad-hoc
// inline types in components.

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

// Video Ingestion + AI Results + B-Roll + Rendering domain types
// (Module 2-5: video pipeline UI).

export type VideoSourceType = 'url' | 'upload';

export type VideoJobStatus =
  | 'pending'
  | 'transcribing'
  | 'analyzing'
  | 'rendering'
  | 'completed'
  | 'partial'
  | 'failed';

export interface VideoJob {
  id: number;
  source_type: VideoSourceType;
  source_url: string | null;
  file_path: string | null;
  title: string | null;
  duration_seconds: number | null;
  status: VideoJobStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export type ShortClipCategory =
  | 'viral'
  | 'educational'
  | 'emotional'
  | 'surprising'
  | 'story'
  | 'other';

export type ShortClipStatus = 'scored' | 'rendering' | 'ready' | 'failed';

export interface ShortClip {
  id: number;
  video_job_id: number;
  rank: number;
  category: ShortClipCategory;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  title: string;
  transcript_excerpt: string;
  hook_strength: number;
  standalone_value: number;
  engagement: number;
  retention: number;
  payoff: number;
  clarity: number;
  shareability: number;
  viral_potential: number;
  b_roll_quality: number;
  overall_score: number;
  status: ShortClipStatus;
  file_path: string | null;
  created_at: string;
}

export type BRollVisualType =
  | 'stock_footage'
  | 'image'
  | 'screenshot'
  | 'screen_recording'
  | 'chart'
  | 'animation';

export interface BRollSuggestion {
  id: number;
  short_clip_id: number;
  start_time: number;
  end_time: number;
  visual_type: BRollVisualType;
  search_keywords: string;
  description: string;
  stock_asset_url: string | null;
}

// --- Analytics module ---

export interface AnalyticsOverview {
  videos_processed: number;
  shorts_generated: number;
  avg_overall_score: number;
  avg_processing_time_seconds: number | null;
}

// --- Admin module ---

export interface AdminUserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AdminStatsResponse {
  total_users: number;
  total_video_jobs: number;
  jobs_by_status: Record<string, number>;
  success_rate: number;
  avg_processing_time_seconds: number | null;
}
