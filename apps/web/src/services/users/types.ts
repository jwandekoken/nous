export type UserRole = "tenant_admin" | "tenant_user";

export interface UserSummary {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string; // ISO date string
}

export interface CreateUserRequest {
  email: string;
  password: string;
}

export interface CreateUserResponse {
  message: string;
  user_id: string;
  email: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  email?: string;
  is_active?: boolean;
  role?: UserRole;
  password?: string;
}

export interface UpdateUserResponse {
  message: string;
  user_id: string;
}

export interface DeleteUserResponse {
  message: string;
  user_id: string;
}

export interface ListUsersRequest {
  page?: number;
  page_size?: number;
  search?: string | null;
  sort_by?: "email" | "created_at";
  sort_order?: "asc" | "desc";
}

export interface ListUsersResponse {
  users: UserSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GetUserResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  tenant_id: string;
}
