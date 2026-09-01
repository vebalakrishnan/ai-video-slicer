import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import {
  getPlatformStats,
  listUsers,
  updateUserStatus,
} from '../services/adminService';
import type { AdminStatsResponse, AdminUserResponse } from '../types';

/** Fetches a paginated list of all users (admin only). */
export function useAdminUsers(
  skip = 0,
  limit = 100,
): UseQueryResult<AdminUserResponse[]> {
  return useQuery({
    queryKey: ['admin', 'users', skip, limit],
    queryFn: () => listUsers(skip, limit),
  });
}

/** Fetches platform-wide usage statistics (admin only). */
export function useAdminStats(): UseQueryResult<AdminStatsResponse> {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getPlatformStats,
  });
}

interface UpdateUserStatusVars {
  userId: number;
  isActive: boolean;
}

/** Mutation to activate/deactivate a user, invalidating the users list on success. */
export function useUpdateUserStatus(): UseMutationResult<
  AdminUserResponse,
  unknown,
  UpdateUserStatusVars
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, isActive }: UpdateUserStatusVars) =>
      updateUserStatus(userId, isActive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
}
