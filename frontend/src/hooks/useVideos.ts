// React Query hooks for the video ingestion / AI results / B-roll /
// rendering pipeline. Thin wrappers over services/videoService.ts
// following the pattern in skills/FRONTEND.md.

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as videoService from '../services/videoService';
import type { BRollSuggestion, ShortClip, VideoJob, VideoJobStatus } from '../types';

const PROCESSING_STATUSES: readonly VideoJobStatus[] = [
  'pending',
  'transcribing',
  'analyzing',
  'rendering',
];

function isProcessing(status: VideoJobStatus): boolean {
  return PROCESSING_STATUSES.includes(status);
}

export function useVideos() {
  return useQuery({
    queryKey: ['videos'],
    queryFn: videoService.listVideos,
  });
}

export function useVideo(id: number | undefined) {
  return useQuery({
    queryKey: ['videos', id],
    queryFn: () => videoService.getVideo(id as number),
    enabled: id !== undefined,
    refetchInterval: (query) => {
      const data = query.state.data as VideoJob | undefined;
      if (data && isProcessing(data.status)) {
        return 3000;
      }
      return false;
    },
  });
}

interface SubmitVideoUrlInput {
  sourceType: 'url';
  sourceUrl: string;
}

interface SubmitVideoUploadInput {
  sourceType: 'upload';
  file: File;
}

type SubmitVideoInput = SubmitVideoUrlInput | SubmitVideoUploadInput;

export function useSubmitVideo() {
  const queryClient = useQueryClient();
  return useMutation<VideoJob, unknown, SubmitVideoInput>({
    mutationFn: (input) =>
      input.sourceType === 'url'
        ? videoService.submitVideoUrl(input.sourceUrl)
        : videoService.submitVideoUpload(input.file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });
}

export function useGenerateShorts() {
  const queryClient = useQueryClient();
  return useMutation<VideoJob, unknown, number>({
    mutationFn: (id) => videoService.generateShorts(id),
    onSuccess: (data, id) => {
      queryClient.setQueryData(['videos', id], data);
      void queryClient.invalidateQueries({ queryKey: ['videos', id] });
    },
  });
}

export function useShorts(videoId: number | undefined) {
  return useQuery({
    queryKey: ['videos', videoId, 'shorts'],
    queryFn: () => videoService.getShorts(videoId as number),
    enabled: videoId !== undefined,
  });
}

export function useShort(id: number | undefined) {
  return useQuery({
    queryKey: ['shorts', id],
    queryFn: () => videoService.getShort(id as number),
    enabled: id !== undefined,
    refetchInterval: (query) => {
      const data = query.state.data as ShortClip | undefined;
      if (data && data.status === 'rendering') {
        return 3000;
      }
      return false;
    },
  });
}

export function useBroll(shortId: number | undefined) {
  return useQuery<BRollSuggestion[]>({
    queryKey: ['shorts', shortId, 'broll'],
    queryFn: () => videoService.getBroll(shortId as number),
    enabled: shortId !== undefined,
  });
}

export function useRenderShort() {
  const queryClient = useQueryClient();
  return useMutation<ShortClip, unknown, number>({
    mutationFn: (id) => videoService.renderShort(id),
    onSuccess: (data, id) => {
      queryClient.setQueryData(['shorts', id], data);
      void queryClient.invalidateQueries({ queryKey: ['shorts', id] });
    },
  });
}

interface ShortVideoUrlState {
  url: string | null;
  isLoading: boolean;
  isError: boolean;
}

/**
 * Fetches a ready short's rendered video through the authenticated API
 * client and exposes it as a local blob: object URL, suitable for a
 * <video src> or a download link. Revokes the previous object URL on
 * every change/unmount so it never leaks.
 */
export function useShortVideoUrl(id: number | undefined, enabled: boolean): ShortVideoUrlState {
  const [state, setState] = useState<ShortVideoUrlState>({
    url: null,
    isLoading: false,
    isError: false,
  });

  useEffect(() => {
    if (!enabled || id === undefined) {
      setState({ url: null, isLoading: false, isError: false });
      return;
    }

    let objectUrl: string | null = null;
    let cancelled = false;

    setState({ url: null, isLoading: true, isError: false });

    videoService
      .getShortVideoBlob(id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ url: objectUrl, isLoading: false, isError: false });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ url: null, isLoading: false, isError: true });
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [id, enabled]);

  return state;
}
