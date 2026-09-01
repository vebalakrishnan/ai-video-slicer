import { Container, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { UserTable } from '../components/admin/UserTable';

/** Admin page for listing users and toggling their active status. */
export function AdminUsersPage() {
  return (
    <PageWrapper>
      <Container maxW="6xl" py={10}>
        <Stack gap={8}>
          <Stack gap={1}>
            <Heading size="xl">Users</Heading>
            <Text color="gray.500">Manage registered accounts.</Text>
          </Stack>
          <UserTable />
        </Stack>
      </Container>
    </PageWrapper>
  );
}

export default AdminUsersPage;
