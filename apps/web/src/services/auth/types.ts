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
