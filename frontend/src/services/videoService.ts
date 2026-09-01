// Thin service wrappers over the shared `api` axios client for the
// video ingestion / AI results / B-roll / rendering pipeline.
//
// Each function maps 1:1 to a backend endpoint (see PRPs/ai-video-slicer-prp.md
// Modules 2-5). Keep these free of React/query concerns — hooks/useVideos.ts
// wraps them with React Query.

import api from './api';
import type { BRollSuggestion, ShortClip, VideoJob } from '../types';

// Trailing slash matches the backend route exactly (@router.post("/") /
// @router.get("/") under the /videos prefix) - without it, FastAPI 307s to
// the slash form, which for a POST forces the browser to re-send the
// entire request body (including a large multipart file upload) a second
// time to complete the redirect.
export async function submitVideoUrl(sourceUrl: string): Promise<VideoJob> {
  const { data } = await api.post<VideoJob>('/videos/', {
    source_url: sourceUrl,
  });
  return data;
}

export async function submitVideoUpload(file: File): Promise<VideoJob> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<VideoJob>('/videos/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

interface VideoJobListResponse {
  videos: VideoJob[];
  total: number;
}

export async function listVideos(): Promise<VideoJob[]> {
  const { data } = await api.get<VideoJobListResponse>('/videos/');
  return data.videos;
}

export async function getVideo(id: number): Promise<VideoJob> {
  const { data } = await api.get<VideoJob>(`/videos/${id}`);
  return data;
}

export async function deleteVideo(id: number): Promise<void> {
  await api.delete(`/videos/${id}`);
}

export async function generateShorts(id: number): Promise<VideoJob> {
  const { data } = await api.post<VideoJob>(`/videos/${id}/generate-shorts`);
  return data;
}

interface ShortClipListResponse {
  shorts: ShortClip[];
  total: number;
}

export async function getShorts(videoId: number): Promise<ShortClip[]> {
  const { data } = await api.get<ShortClipListResponse>(`/videos/${videoId}/shorts`);
  return data.shorts;
}

export async function getShort(id: number): Promise<ShortClip> {
  const { data } = await api.get<ShortClip>(`/shorts/${id}`);
  return data;
}

export async function getBroll(shortId: number): Promise<BRollSuggestion[]> {
  const { data } = await api.get<BRollSuggestion[]>(`/shorts/${shortId}/broll`);
  return data;
}

export async function renderShort(id: number): Promise<ShortClip> {
  const { data } = await api.post<ShortClip>(`/shorts/${id}/render`);
  return data;
}

/**
 * Fetches a rendered short's video as a Blob through the authenticated
 * axios client. The download endpoint requires a Bearer token (it's
 * user-owned content, not public), so a plain `<video src>` / `<a href>` /
 * `window.open` pointed at the raw URL gets a 401 - the browser never
 * attaches the axios interceptor's Authorization header to those. Callers
 * build an object URL from the returned Blob instead (see useShortVideoUrl).
 */
export async function getShortVideoBlob(id: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/shorts/${id}/download`, {
    responseType: 'blob',
  });
  return data;
}
