import api from './api';
import type { AdminStatsResponse, AdminUserResponse } from '../types';

/** Thin wrapper around GET /admin/users — paginated list of all users. */
export async function listUsers(
  skip = 0,
  limit = 100,
): Promise<AdminUserResponse[]> {
  const { data } = await api.get<AdminUserResponse[]>('/admin/users', {
    params: { skip, limit },
  });
  return data;
}

/** Thin wrapper around PUT /admin/users/{id} — update a user's active status. */
export async function updateUserStatus(
  userId: number,
  isActive: boolean,
): Promise<AdminUserResponse> {
  const { data } = await api.put<AdminUserResponse>(`/admin/users/${userId}`, {
    is_active: isActive,
  });
  return data;
}

/** Thin wrapper around GET /admin/stats — platform-wide usage statistics. */
export async function getPlatformStats(): Promise<AdminStatsResponse> {
  const { data } = await api.get<AdminStatsResponse>('/admin/stats');
  return data;
}
