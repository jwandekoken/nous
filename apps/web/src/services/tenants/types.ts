export interface CreateTenantRequest {
  name: string;
  email: string;
  password: string;
}

export interface CreateTenantResponse {
  message: string;
  tenant_id: string;
  user_id: string;
}

export interface UpdateTenantRequest {
  name: string;
}

export interface UpdateTenantResponse {
  message: string;
  tenant_id: string;
}

export interface DeleteTenantResponse {
  message: string;
  tenant_id: string;
}

export interface TenantSummary {
  id: string;
  name: string;
  age_graph_name: string;
  created_at: string; // ISO date string
  user_count: number;
}

export interface ListTenantsRequest {
  page?: number;
  page_size?: number;
  search?: string | null;
  sort_by?: "name" | "created_at";
  sort_order?: "asc" | "desc";
}

export interface ListTenantsResponse {
  tenants: TenantSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
