import { Badge, Table, Text } from '@chakra-ui/react';
import { GradientButton } from '../ui/GradientButton';
import { useAdminUsers, useUpdateUserStatus } from '../../hooks/useAdmin';
import type { AdminUserResponse } from '../../types';

interface UserRowProps {
  user: AdminUserResponse;
}

function UserRow({ user }: UserRowProps) {
  const { mutate, isPending, variables } = useUpdateUserStatus();
  const isTogglingThisUser = isPending && variables?.userId === user.id;

  return (
    <Table.Row>
      <Table.Cell>{user.email}</Table.Cell>
      <Table.Cell>{user.full_name ?? '—'}</Table.Cell>
      <Table.Cell>
        <Badge colorPalette={user.is_admin ? 'purple' : 'gray'}>
          {user.is_admin ? 'Admin' : 'User'}
        </Badge>
      </Table.Cell>
      <Table.Cell>
        <Badge colorPalette={user.is_active ? 'green' : 'red'}>
          {user.is_active ? 'Active' : 'Inactive'}
        </Badge>
      </Table.Cell>
      <Table.Cell>{new Date(user.created_at).toLocaleDateString()}</Table.Cell>
      <Table.Cell>
        <GradientButton
          size="sm"
          loading={isTogglingThisUser}
          onClick={() =>
            mutate({ userId: user.id, isActive: !user.is_active })
          }
        >
          {user.is_active ? 'Deactivate' : 'Activate'}
        </GradientButton>
      </Table.Cell>
    </Table.Row>
  );
}

/** Chakra Table listing all users with an active/inactive toggle per row. */
export function UserTable() {
  const { data: users, isLoading, isError } = useAdminUsers();

  if (isLoading) {
    return <Text color="gray.500">Loading users...</Text>;
  }

  if (isError || !users) {
    return <Text color="red.500">Failed to load users.</Text>;
  }

  return (
    <Table.Root variant="outline" borderRadius="xl" overflow="hidden">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>Email</Table.ColumnHeader>
          <Table.ColumnHeader>Name</Table.ColumnHeader>
          <Table.ColumnHeader>Role</Table.ColumnHeader>
          <Table.ColumnHeader>Status</Table.ColumnHeader>
          <Table.ColumnHeader>Joined</Table.ColumnHeader>
          <Table.ColumnHeader>Actions</Table.ColumnHeader>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {users.map((user) => (
          <UserRow key={user.id} user={user} />
        ))}
      </Table.Body>
    </Table.Root>
  );
}
