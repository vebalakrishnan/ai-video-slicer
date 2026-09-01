import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tabs, Text, VStack } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useSubmitVideo } from '../../hooks/useVideos';

// Matches MAX_UPLOAD_BYTES in backend/app/routers/videos.py - checked
// client-side too so a too-large file is rejected instantly instead of
// only after uploading the whole thing to the server.
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB
const MAX_UPLOAD_LABEL = '2 GB';
const ALLOWED_UPLOAD_EXTENSIONS = ['.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'];

/**
 * Tabbed form to submit a video either by pasting a URL or picking a file to
 * upload. On success, navigates to the new video's status page.
 */
export function UrlOrUploadForm() {
  const navigate = useNavigate();
  const submitVideo = useSubmitVideo();

  const [sourceUrl, setSourceUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleUrlSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);

    if (!sourceUrl.trim()) {
      setFormError('Enter a video URL.');
      return;
    }

    try {
      const video = await submitVideo.mutateAsync({ sourceType: 'url', sourceUrl: sourceUrl.trim() });
      navigate(`/videos/${video.id}`);
    } catch {
      setFormError('Could not submit the video. Please try again.');
    }
  };

  const handleUploadSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);

    if (!file) {
      setFormError('Choose a video file to upload.');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setFormError(`This file is too large. Maximum upload size is ${MAX_UPLOAD_LABEL}.`);
      return;
    }

    try {
      const video = await submitVideo.mutateAsync({ sourceType: 'upload', file });
      navigate(`/videos/${video.id}`);
    } catch {
      setFormError('Could not upload the video. Please try again.');
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>): void => {
    setFile(event.target.files?.[0] ?? null);
  };

  return (
    <Tabs.Root defaultValue="url" colorPalette="purple">
      <Tabs.List mb={6}>
        <Tabs.Trigger value="url">Paste URL</Tabs.Trigger>
        <Tabs.Trigger value="upload">Upload File</Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="url">
        <form onSubmit={(e) => void handleUrlSubmit(e)}>
          <VStack align="stretch" gap={4}>
            <AnimatedInput
              label="Video URL"
              placeholder="https://youtube.com/watch?v=..."
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
            {formError && (
              <Text color="red.500" fontSize="sm">
                {formError}
              </Text>
            )}
            <GradientButton type="submit" disabled={submitVideo.isPending}>
              {submitVideo.isPending ? 'Submitting…' : 'Submit Video'}
            </GradientButton>
          </VStack>
        </form>
      </Tabs.Content>

      <Tabs.Content value="upload">
        <form onSubmit={(e) => void handleUploadSubmit(e)}>
          <VStack align="stretch" gap={4}>
            <AnimatedInput
              label="Video File"
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              px={3}
              py={2}
            />
            <Text color="gray.500" fontSize="xs">
              Maximum size: {MAX_UPLOAD_LABEL}. Formats: {ALLOWED_UPLOAD_EXTENSIONS.join(', ')}.
            </Text>
            {formError && (
              <Text color="red.500" fontSize="sm">
                {formError}
              </Text>
            )}
            <GradientButton type="submit" disabled={submitVideo.isPending}>
              {submitVideo.isPending ? 'Uploading…' : 'Upload Video'}
            </GradientButton>
          </VStack>
        </form>
      </Tabs.Content>
    </Tabs.Root>
  );
}
