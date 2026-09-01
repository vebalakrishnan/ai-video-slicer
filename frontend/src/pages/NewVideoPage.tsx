import { Container, Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { UrlOrUploadForm } from '../components/video/UrlOrUploadForm';

export function NewVideoPage() {
  return (
    <PageWrapper>
      <Container maxW="2xl" py={10}>
        <VStack align="stretch" gap={6}>
          <Heading size="lg">Submit a New Video</Heading>
          <GlassCard>
            <UrlOrUploadForm />
          </GlassCard>
        </VStack>
      </Container>
    </PageWrapper>
  );
}
