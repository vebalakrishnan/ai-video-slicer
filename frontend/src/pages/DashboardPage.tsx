import { useNavigate } from 'react-router-dom';
import { Container, Flex, Heading } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GradientButton } from '../components/ui/GradientButton';
import { VideoJobList } from '../components/video/VideoJobList';
import { useVideos } from '../hooks/useVideos';

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: videos, isLoading } = useVideos();

  return (
    <PageWrapper>
      <Container maxW="4xl" py={10}>
        <Flex justify="space-between" align="center" mb={8} wrap="wrap" gap={4}>
          <Heading size="lg">Your Videos</Heading>
          <GradientButton onClick={() => navigate('/videos/new')}>New Video</GradientButton>
        </Flex>
        <VideoJobList videos={videos ?? []} isLoading={isLoading} />
      </Container>
    </PageWrapper>
  );
}
