export interface LoginCredentials {
  email: string;
  password: string;
}

export type UserRole = "super_admin" | "tenant_admin" | "tenant_user";

export interface CurrentUser {
  id: string;
  email: string;
  role: UserRole;
  tenant_id: string | null;
}

export interface RefreshTokensResponse {
  message: string;
  token_type: string;
}

export interface SetupRequiredResponse {
  setup_required: boolean;
}

export interface SetupAdminRequest {
  email: string;
  password: string;
}

export interface SetupAdminResponse {
  message: string;
  email: string;
}
